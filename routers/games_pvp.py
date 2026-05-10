# routers/games_pvp.py
# =====================================================
# SPACE DONUT PVP — Игрок против Игрока
# =====================================================

import asyncio
import random
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import config
import database
from handlers.security import get_current_user

# Live exchange-rate helpers shared with gifts router
try:
    from routers.gifts import (
        _fetch_portal_floor_price_async,
        _fetch_ton_to_stars_rate,
        _apply_exchange_bonus,
    )
    _live_exchange_available = True
except Exception:
    _live_exchange_available = False

router = APIRouter(prefix="/pvp", tags=["pvp"])

# ─────────────────────────────────────────────────────────────
# ПАРАМЕТРЫ
# ─────────────────────────────────────────────────────────────

COUNTDOWN_DURATION = 15.0   # секунд обратного отсчёта после 2+ игроков
ROLLING_DURATION   = 6.5    # секунд анимации шарика
FINISHED_DURATION  = 7.0    # секунд показа победителя

MIN_BET_STARS   = 50
MIN_BET_DONUTS  = 0.1

COMMISSION_STARS  = 0.05    # 5% комиссия на звёзды
COMMISSION_DONUTS = 0.05    # 5% комиссия на пончики

PLAYER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8", "#F0A500",
]

# ─────────────────────────────────────────────────────────────
# ГЛОБАЛЬНОЕ СОСТОЯНИЕ
# ─────────────────────────────────────────────────────────────

_lock = asyncio.Lock()

# ─────────────────────────────────────────────────────────────
# КЭШИРОВАННЫЙ ЖИВОЙ КУРС ПОНЧИК → ЗВЁЗДЫ
# ─────────────────────────────────────────────────────────────

_cached_live_donuts_rate: float = 0.0
_cached_rate_timestamp: float = 0.0
DONUTS_RATE_CACHE_TTL: float = 30.0  # обновляем каждые 30 секунд


async def _get_live_donuts_to_stars_rate() -> float:
    """Возвращает актуальный курс 1 TON (= 1 пончик) → звёзды.
    Данные берутся из того же API, что и в разделе обмена.
    При недоступности API возвращает config.DONUTS_TO_STARS_RATE."""
    global _cached_live_donuts_rate, _cached_rate_timestamp
    now = time.time()
    if _live_exchange_available and (
        now - _cached_rate_timestamp > DONUTS_RATE_CACHE_TTL
        or _cached_live_donuts_rate <= 0
    ):
        try:
            rate = await _fetch_ton_to_stars_rate()
            if rate and rate > 0:
                _cached_live_donuts_rate = float(rate)
                _cached_rate_timestamp = now
        except Exception as e:
            print(f"[PvP] failed to fetch live donut rate: {e}")
    return _cached_live_donuts_rate if _cached_live_donuts_rate > 0 else config.DONUTS_TO_STARS_RATE

pvp_round: Dict[str, Any] = {
    "id":            0,
    "state":         "waiting",   # waiting | countdown | rolling | finished
    "countdown_end": 0.0,
    "rolling_end":      0.0,
    "rolling_start_ts": 0.0,
    "ball_seed":        0,
    "ball_target_x":    50.0,
    "ball_target_y":    50.0,
    "finished_end":  0.0,
    "players":       {},          # {user_id: {name, avatar, color, bets: [...]}}
    "winner_id":     None,
    "last_game":     None,
    "best_game":     None,
    "_color_idx":    0,
}


# ─────────────────────────────────────────────────────────────
# MULBERRY32 PRNG — ИДЕНТИЧЕН КЛИЕНТСКОЙ РЕАЛИЗАЦИИ (JS)
# Позволяет серверу вычислить финальную точку шарика один раз,
# чтобы все клиенты видели одинаковую анимацию независимо от
# текущего курса пончиков.
# ─────────────────────────────────────────────────────────────

def _mulberry32(seed: int):
    """Псевдослучайный генератор Mulberry32 (float 0..1).
    Полностью совместим с реализацией в games-pvp.js."""
    s = [seed & 0xFFFFFFFF]

    def _imul32(a: int, b: int) -> int:
        return (a * b) & 0xFFFFFFFF

    def rng() -> float:
        s[0] = (s[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = _imul32(s[0] ^ (s[0] >> 15), 1 | s[0])
        t = (t ^ ((t + _imul32(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rng


def _compute_ball_target(seed: int, winner_id: int, players: list) -> dict:
    """Вычисляет координаты финальной точки шарика, используя тот же
    алгоритм и PRNG, что клиент (getPvpWinnerSectorTarget).
    Потребляет ровно 2 вызова PRNG, чтобы последующая траектория
    рикошетов была идентична на всех клиентах."""
    import math
    rng = _mulberry32(seed)

    total_chance = sum(p["win_chance"] for p in players)
    current_percent = 0.0

    for p in players:
        normalized_chance = (
            (p["win_chance"] / total_chance * 100) if total_chance > 0
            else (100 / len(players))
        )
        if str(p["user_id"]) == str(winner_id):
            padding = max(2.0, normalized_chance * 0.1)
            safe_chance = max(1.0, normalized_chance - padding * 2)
            random_percent = current_percent + padding + (rng() * safe_chance)  # вызов 1
            angle_rad = ((random_percent * 3.6) - 90) * (math.pi / 180)
            r = 12 + rng() * 16  # вызов 2
            return {
                "x": round(50 + r * math.cos(angle_rad), 4),
                "y": round(50 + r * math.sin(angle_rad), 4),
            }
        current_percent += normalized_chance

    return {"x": 50.0, "y": 50.0}

# ─────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────

def _get_gift_value_stars(gift_id: int) -> int:
    """Возвращает стоимость подарка в звёздах для вычисления шанса победы."""
    for catalog in (config.TG_GIFTS, config.BASE_GIFTS, config.MAIN_GIFTS):
        gift = catalog.get(gift_id)
        if gift:
            return gift.get("required_value") or gift.get("value") or 1
    return 1


def _get_gift_info(gift_id: int) -> dict:
    for catalog in (config.TG_GIFTS, config.BASE_GIFTS, config.MAIN_GIFTS):
        if gift_id in catalog:
            return catalog[gift_id]
    return {}


async def _get_live_gift_value_stars(gift_id: int, gift_info: dict) -> int:
    """Fetch live exchange value for a gift using Portal Market pricing.
    Mirrors the /pvp/inventory endpoint exactly so win-chance weights
    reflect the real market value the player sees in the UI."""
    if not _live_exchange_available:
        return _get_gift_value_stars(gift_id)
    try:
        ton_to_stars = await _fetch_ton_to_stars_rate()

        # TG gifts: fixed bonus formula (same as inventory + exchange handler)
        if gift_id in config.TG_GIFTS:
            return _get_gift_value_stars(gift_id) + 10

        gift_name = gift_info.get("name", "")
        ton_price = await _fetch_portal_floor_price_async(gift_name) if gift_name else None

        if not ton_price or ton_price <= 0:
            stored = gift_info.get("value") or gift_info.get("required_value") or 0
            if gift_id in config.BASE_GIFTS:
                ton_price = stored / 0.80 if stored > 0 else 0
            else:
                ton_price = stored / 1.20 if stored > 0 else 0

        if ton_price and ton_price > 0 and ton_to_stars:
            base_stars = max(1, int(ton_price * ton_to_stars))
            return await _apply_exchange_bonus(base_stars)
    except Exception as e:
        print(f"[PvP] live gift value error for gift {gift_id}: {e}")

    return _get_gift_value_stars(gift_id)


def _player_total_stars(player: dict, donuts_rate: float = 0) -> float:
    """Суммарная стоимость ставок игрока в эквиваленте звёзд.
    donuts_rate: живой курс пончик→звёзды (1 пончик = 1 TON в звёздах);
    если 0, берётся из config."""
    rate = donuts_rate if donuts_rate > 0 else config.DONUTS_TO_STARS_RATE
    total = 0.0
    for bet in player["bets"]:
        if bet["type"] == "stars":
            total += bet["amount"]
        elif bet["type"] == "donuts":
            total += bet["amount"] * rate
        elif bet["type"] == "gift":
            total += bet.get("value_stars", 1)
    return total


def _build_player_list(donuts_rate: float = 0.0) -> list:
    total_pot = sum(_player_total_stars(p, donuts_rate) for p in pvp_round["players"].values())
    result = []
    for uid, player in pvp_round["players"].items():
        ps = _player_total_stars(player, donuts_rate)
        win_chance = (ps / total_pot * 100) if total_pot > 0 else 0
        result.append({
            "user_id":    uid,
            "name":       player["name"],
            "avatar":     player["avatar"],
            "color":      player["color"],
            "win_chance": round(win_chance, 1),
            "stars_bet":  sum(b["amount"] for b in player["bets"] if b["type"] == "stars"),
            "donuts_bet": round(sum(b["amount"] for b in player["bets"] if b["type"] == "donuts"), 2),
            "gift_bets":  [b for b in player["bets"] if b["type"] == "gift"],
            "value_stars": round(ps, 2),
        })
    return result


async def _determine_winner() -> Optional[int]:
    """Случайный выбор победителя с весами по стоимости ставок (живой курс пончиков)."""
    live_rate = await _get_live_donuts_to_stars_rate()
    weights = {
        uid: _player_total_stars(player, live_rate)
        for uid, player in pvp_round["players"].items()
    }
    valid = {k: v for k, v in weights.items() if v > 0}
    if not valid:
        return None
    ids = list(valid.keys())
    ws  = [valid[uid] for uid in ids]
    return random.choices(ids, weights=ws, k=1)[0]


async def _payout_winner(winner_id: int):
    """Начисляет победителю весь банк минус комиссия и переносит подарки."""
    try:
        players = pvp_round["players"]
        if winner_id not in players:
            return

        total_stars  = sum(
            sum(b["amount"] for b in p["bets"] if b["type"] == "stars")
            for p in players.values()
        )
        total_donuts = sum(
            sum(b["amount"] for b in p["bets"] if b["type"] == "donuts")
            for p in players.values()
        )
        all_gift_bets = [
            b for p in players.values()
            for b in p["bets"] if b["type"] == "gift"
        ]

        payout_stars  = int(total_stars * (1 - COMMISSION_STARS))
        payout_donuts = round(total_donuts * (1 - COMMISSION_DONUTS), 4)

        if payout_stars > 0:
            await database.add_stars_to_user(winner_id, payout_stars)
            my_stars = sum(b["amount"] for b in players[winner_id]["bets"] if b["type"] == "stars")
            await database.add_history_entry(
                winner_id, "pvp_win_stars",
                f"Space PvP победа ({len(players)} игр.)", payout_stars - my_stars
            )

        if payout_donuts > 0:
            await database.add_points_to_user(winner_id, payout_donuts)
            my_donuts = sum(b["amount"] for b in players[winner_id]["bets"] if b["type"] == "donuts")
            await database.add_history_entry(
                winner_id, "pvp_win_donuts",
                f"Space PvP победа (пончики)", round(payout_donuts - my_donuts, 4)
            )

        for gb in all_gift_bets:
            await database.add_gift_to_user(winner_id, gb["gift_id"], 1)

        # Обновить статистику лучшей/последней игры
        gifts_value_stars = sum(b.get("value_stars", 1) for b in all_gift_bets)
        total_value_stars = (
            int(payout_stars)
            + int(payout_donuts * config.DONUTS_TO_STARS_RATE)
            + int(gifts_value_stars * (1 - COMMISSION_STARS))
        )
        game_info = {
            "name":             players[winner_id]["name"],
            "avatar":           players[winner_id]["avatar"],
            "color":            players[winner_id]["color"],
            "total_stars":      payout_stars,
            "total_donuts":     payout_donuts,
            "gifts_count":      len(all_gift_bets),
            "player_count":     len(players),
            "total_value_stars": total_value_stars,
        }
        pvp_round["last_game"] = game_info
        if (pvp_round["best_game"] is None
                or total_value_stars > pvp_round["best_game"].get("total_value_stars", 0)):
            pvp_round["best_game"] = game_info

    except Exception as e:
        print(f"[PvP] payout_winner error: {e}")


def _ensure_player(user_id: int, user_info: dict):
    """Добавляет игрока в раунд если ещё не участвует (вызывать под локом)."""
    if user_id not in pvp_round["players"]:
        idx = pvp_round["_color_idx"] % len(PLAYER_COLORS)
        pvp_round["_color_idx"] += 1
        pvp_round["players"][user_id] = {
            "name":   user_info.get("first_name") or user_info.get("username") or "Игрок",
            "avatar": user_info.get("photo_url", ""),
            "color":  PLAYER_COLORS[idx],
            "bets":   [],
        }


# ─────────────────────────────────────────────────────────────
# ФОНОВАЯ ЗАДАЧА — МЕНЕДЖЕР РАУНДОВ
# ─────────────────────────────────────────────────────────────

async def pvp_round_manager():
    while True:
        try:
            async with _lock:
                state = pvp_round["state"]

            if state == "waiting":
                async with _lock:
                    if len(pvp_round["players"]) >= 2 and pvp_round["state"] == "waiting":
                        pvp_round["state"]        = "countdown"
                        pvp_round["countdown_end"] = time.time() + COUNTDOWN_DURATION
                await asyncio.sleep(0.5)

            elif state == "countdown":
                if time.time() >= pvp_round["countdown_end"]:
                    async with _lock:
                        if pvp_round["state"] == "countdown":
                            live_rate = await _get_live_donuts_to_stars_rate()
                            winner_id = await _determine_winner()
                            ball_seed = random.randint(1, 999999)

                            # Вычисляем финальную точку шарика на сервере один раз,
                            # используя живой курс в момент старта раунда.
                            # Все клиенты получат одинаковые координаты и увидят
                            # идентичную анимацию независимо от своего текущего курса.
                            players_snap = _build_player_list(live_rate)
                            if winner_id and players_snap:
                                target = _compute_ball_target(ball_seed, winner_id, players_snap)
                            else:
                                target = {"x": 50.0, "y": 50.0}

                            pvp_round["winner_id"]        = winner_id
                            pvp_round["state"]            = "rolling"
                            pvp_round["rolling_end"]      = time.time() + ROLLING_DURATION
                            pvp_round["rolling_start_ts"] = time.time()
                            pvp_round["ball_seed"]        = ball_seed
                            pvp_round["ball_target_x"]    = target["x"]
                            pvp_round["ball_target_y"]    = target["y"]
                await asyncio.sleep(0.2)

            elif state == "rolling":
                if time.time() >= pvp_round["rolling_end"]:
                    async with _lock:
                        if pvp_round["state"] == "rolling":
                            pvp_round["state"]        = "finished"
                            pvp_round["finished_end"] = time.time() + FINISHED_DURATION
                            if pvp_round["winner_id"]:
                                asyncio.create_task(_payout_winner(pvp_round["winner_id"]))
                await asyncio.sleep(0.2)

            elif state == "finished":
                if time.time() >= pvp_round["finished_end"]:
                    async with _lock:
                        if pvp_round["state"] == "finished":
                            pvp_round["id"]           += 1
                            pvp_round["state"]         = "waiting"
                            pvp_round["countdown_end"] = 0.0
                            pvp_round["rolling_end"]   = 0.0
                            pvp_round["rolling_start_ts"] = 0.0
                            pvp_round["finished_end"]  = 0.0
                            pvp_round["ball_seed"]     = 0
                            pvp_round["ball_target_x"] = 50.0
                            pvp_round["ball_target_y"] = 50.0
                            pvp_round["players"]       = {}
                            pvp_round["winner_id"]     = None
                            pvp_round["_color_idx"]    = 0
                await asyncio.sleep(0.5)

            else:
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[PvP] round_manager error: {e}")
            await asyncio.sleep(2.0)


# ─────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ API
# ─────────────────────────────────────────────────────────────

@router.get("/state")
async def get_pvp_state(current_user: dict = Depends(get_current_user)):
    # Fetch live donut→stars rate BEFORE acquiring the lock (network call)
    live_rate = await _get_live_donuts_to_stars_rate()

    async with _lock:
        state        = pvp_round["state"]
        round_id     = pvp_round["id"]
        countdown_end = pvp_round["countdown_end"]
        winner_id    = pvp_round["winner_id"] if state in ("finished", "rolling") else None
        last_game    = pvp_round["last_game"]
        best_game    = pvp_round["best_game"]
        players      = _build_player_list(live_rate)

    time_left = max(0.0, countdown_end - time.time()) if countdown_end > 0 else 0.0
    total_stars  = sum(p.get("stars_bet", 0) for p in players)
    total_donuts = round(sum(p.get("donuts_bet", 0) for p in players), 2)
    total_gifts  = sum(len(p.get("gift_bets", [])) for p in players)

    # Collect unique gift previews (photo + name) for pot display in UI
    gift_previews: list = []
    seen_gifts: set = set()
    for p in players:
        for gb in (p.get("gift_bets") or []):
            gid = gb.get("gift_id")
            if gid and gid not in seen_gifts:
                seen_gifts.add(gid)
                gift_previews.append({
                    "gift_id": gid,
                    "name":    gb.get("gift_name", ""),
                    "photo":   gb.get("gift_photo", ""),
                })

    winner_data = None
    if winner_id and state in ("rolling", "finished"):
        wp = pvp_round["players"].get(winner_id, {})
        winner_data = {
            "user_id": winner_id,
            "name":    wp.get("name", "?"),
            "avatar":  wp.get("avatar", ""),
            "color":   wp.get("color", "#FF6B6B"),
        }

    return {
        "round_id":        round_id,
        "state":           state,
        "time_left":       round(time_left, 2),
        "rolling_start_ts": pvp_round.get("rolling_start_ts", 0),
        "ball_seed":        pvp_round.get("ball_seed", 0),
        "ball_target_x":   pvp_round.get("ball_target_x", 50.0),
        "ball_target_y":   pvp_round.get("ball_target_y", 50.0),
        "players":         players,
        "winner":          winner_data,
        "pot":             {"stars": total_stars, "donuts": total_donuts, "gifts": total_gifts, "gift_previews": gift_previews},
        "last_game":       last_game,
        "best_game":       best_game,
    }


class BetStarsRequest(BaseModel):
    amount: int

class BetDonutsRequest(BaseModel):
    amount: float

class BetGiftRequest(BaseModel):
    gift_id: int


@router.post("/bet/stars")
async def bet_stars(data: BetStarsRequest, current_user: dict = Depends(get_current_user)):
    tg_id  = current_user["id"]
    amount = data.amount

    if amount < MIN_BET_STARS:
        raise HTTPException(400, f"Минимальная ставка {MIN_BET_STARS} ⭐")

    async with _lock:
        if pvp_round["state"] not in ("waiting", "countdown"):
            raise HTTPException(400, "Ставки сейчас не принимаются")

    ok = await database.deduct_stars(tg_id, amount)
    if not ok:
        raise HTTPException(400, "Недостаточно звёзд")

    async with _lock:
        if pvp_round["state"] not in ("waiting", "countdown"):
            await database.add_stars_to_user(tg_id, amount)
            raise HTTPException(400, "Ставки сейчас не принимаются")
        _ensure_player(tg_id, current_user)
        pvp_round["players"][tg_id]["bets"].append({"type": "stars", "amount": amount})

    updated = await database.get_user_data(tg_id)
    return {"status": "ok", "balance": updated["balance"], "stars": updated["stars"],
            "gifts": await database.get_user_gifts(tg_id)}


@router.post("/bet/donuts")
async def bet_donuts(data: BetDonutsRequest, current_user: dict = Depends(get_current_user)):
    tg_id  = current_user["id"]
    amount = round(data.amount, 2)

    if amount < MIN_BET_DONUTS:
        raise HTTPException(400, f"Минимальная ставка {MIN_BET_DONUTS} 🍩")

    async with _lock:
        if pvp_round["state"] not in ("waiting", "countdown"):
            raise HTTPException(400, "Ставки сейчас не принимаются")

    ok = await database.deduct_balance(tg_id, amount)
    if not ok:
        raise HTTPException(400, "Недостаточно пончиков")

    async with _lock:
        if pvp_round["state"] not in ("waiting", "countdown"):
            await database.add_points_to_user(tg_id, amount)
            raise HTTPException(400, "Ставки сейчас не принимаются")
        _ensure_player(tg_id, current_user)
        pvp_round["players"][tg_id]["bets"].append({"type": "donuts", "amount": amount})

    updated = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)
    return {"status": "ok", "balance": updated["balance"], "stars": updated["stars"],
            "gifts": updated_gifts}


@router.post("/bet/gift")
async def bet_gift(data: BetGiftRequest, current_user: dict = Depends(get_current_user)):
    tg_id   = current_user["id"]
    gift_id = data.gift_id

    async with _lock:
        if pvp_round["state"] not in ("waiting", "countdown"):
            raise HTTPException(400, "Ставки сейчас не принимаются")

    gift_info = _get_gift_info(gift_id)
    if not gift_info:
        raise HTTPException(400, "Подарок не найден")

    value_stars = await _get_live_gift_value_stars(gift_id, gift_info)

    ok = await database.remove_gift_from_user(tg_id, gift_id)
    if not ok:
        raise HTTPException(400, "Подарок не найден в инвентаре")

    async with _lock:
        if pvp_round["state"] not in ("waiting", "countdown"):
            await database.add_gift_to_user(tg_id, gift_id, 1)
            raise HTTPException(400, "Ставки сейчас не принимаются")
        _ensure_player(tg_id, current_user)
        pvp_round["players"][tg_id]["bets"].append({
            "type":       "gift",
            "gift_id":    gift_id,
            "gift_name":  gift_info.get("name", ""),
            "gift_photo": gift_info.get("photo", ""),
            "value_stars": value_stars,
            "amount":     1,
        })

    updated = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)
    return {"status": "ok", "balance": updated["balance"], "stars": updated["stars"],
            "gifts": updated_gifts}


@router.get("/inventory")
async def get_inventory(current_user: dict = Depends(get_current_user)):
    """Инвентарь пользователя для выбора подарков в PvP с ценами в звёздах по курсу обмена.
    Использует живой курс Portal Market (тот же, что /api/exchange-preview в профиле)."""
    tg_id  = current_user["id"]
    gifts  = await database.get_user_gifts(tg_id)

    # Fetch live rate once for all non-TG gifts
    ton_to_stars = None
    if _live_exchange_available:
        try:
            ton_to_stars = await _fetch_ton_to_stars_rate()
        except Exception:
            ton_to_stars = None

    result = []
    for gift_id, amount in gifts.items():
        info = _get_gift_info(gift_id)
        if not info:
            continue

        raw_value = _get_gift_value_stars(gift_id)

        # TG gifts: fixed bonus formula (same as exchange handler)
        if gift_id in config.TG_GIFTS:
            exchange_stars = raw_value + 10

        elif _live_exchange_available and gift_id not in config.TG_GIFTS:
            # Try live Portal Market price — mirrors /api/exchange-preview exactly
            gift_name = info.get("name", "")
            try:
                ton_price = await _fetch_portal_floor_price_async(gift_name) if gift_name else None
            except Exception:
                ton_price = None

            if not ton_price or ton_price <= 0:
                # Fallback formula (same as exchange-preview fallback)
                stored = info.get("value") or info.get("required_value") or 0
                if gift_id in config.BASE_GIFTS:
                    ton_price = stored / 0.80 if stored > 0 else 0
                else:
                    ton_price = stored / 1.20 if stored > 0 else 0

            if ton_price and ton_price > 0 and ton_to_stars:
                base_stars = max(1, int(ton_price * ton_to_stars))
                try:
                    exchange_stars = await _apply_exchange_bonus(base_stars)
                except Exception:
                    exchange_stars = base_stars
            else:
                # Last-resort static fallback
                if gift_id in config.BASE_GIFTS:
                    exchange_stars = max(1, int(raw_value / 0.80 * 1.1))
                else:
                    exchange_stars = max(1, int(raw_value / 1.20 * 1.1))
        else:
            # Static fallback when live exchange is unavailable
            if gift_id in config.BASE_GIFTS:
                exchange_stars = max(1, int(raw_value / 0.80 * 1.1))
            else:
                exchange_stars = max(1, int(raw_value / 1.20 * 1.1))

        result.append({
            "gift_id":        gift_id,
            "name":           info.get("name", ""),
            "photo":          info.get("photo", ""),
            "value_stars":    raw_value,
            "exchange_stars": exchange_stars,
            "amount":         amount,
        })
    return {"gifts": result}


@router.get("/user_balance")
async def get_user_balance(current_user: dict = Depends(get_current_user)):
    """Быстрое обновление баланса и инвентаря для синхронизации после игры."""
    tg_id      = current_user["id"]
    user_data  = await database.get_user_data(tg_id)
    user_gifts = await database.get_user_gifts(tg_id)
    return {
        "balance": user_data.get("balance", 0),
        "stars":   user_data.get("stars", 0),
        "gifts":   user_gifts,
}
