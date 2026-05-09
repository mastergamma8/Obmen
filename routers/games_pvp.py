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

pvp_round: Dict[str, Any] = {
    "id":            0,
    "state":         "waiting",   # waiting | countdown | rolling | finished
    "countdown_end": 0.0,
    "rolling_end":   0.0,
    "finished_end":  0.0,
    "players":       {},          # {user_id: {name, avatar, color, bets: [...]}}
    "winner_id":     None,
    "last_game":     None,
    "best_game":     None,
    "_color_idx":    0,
}

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


def _player_total_stars(player: dict) -> float:
    """Суммарная стоимость ставок игрока в эквиваленте звёзд."""
    total = 0.0
    for bet in player["bets"]:
        if bet["type"] == "stars":
            total += bet["amount"]
        elif bet["type"] == "donuts":
            total += bet["amount"] * config.DONUTS_TO_STARS_RATE
        elif bet["type"] == "gift":
            total += bet.get("value_stars", 1)
    return total


def _build_player_list() -> list:
    total_pot = sum(_player_total_stars(p) for p in pvp_round["players"].values())
    result = []
    for uid, player in pvp_round["players"].items():
        ps = _player_total_stars(player)
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
    """Случайный выбор победителя с весами по стоимости ставок."""
    weights = {
        uid: _player_total_stars(player)
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
                or payout_stars > pvp_round["best_game"].get("total_stars", 0)):
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
                            winner_id = await _determine_winner()
                            pvp_round["winner_id"]   = winner_id
                            pvp_round["state"]       = "rolling"
                            pvp_round["rolling_end"] = time.time() + ROLLING_DURATION
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
                            pvp_round["finished_end"]  = 0.0
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
    async with _lock:
        state        = pvp_round["state"]
        round_id     = pvp_round["id"]
        countdown_end = pvp_round["countdown_end"]
        winner_id    = pvp_round["winner_id"] if state == "finished" else None
        last_game    = pvp_round["last_game"]
        best_game    = pvp_round["best_game"]
        players      = _build_player_list()

    time_left = max(0.0, countdown_end - time.time()) if countdown_end > 0 else 0.0
    total_stars  = sum(p.get("stars_bet", 0) for p in players)
    total_donuts = round(sum(p.get("donuts_bet", 0) for p in players), 2)
    total_gifts  = sum(len(p.get("gift_bets", [])) for p in players)

    winner_data = None
    if winner_id and state == "finished":
        wp = pvp_round["players"].get(winner_id, {})
        winner_data = {
            "user_id": winner_id,
            "name":    wp.get("name", "?"),
            "avatar":  wp.get("avatar", ""),
            "color":   wp.get("color", "#FF6B6B"),
        }

    return {
        "round_id":   round_id,
        "state":      state,
        "time_left":  round(time_left, 2),
        "players":    players,
        "winner":     winner_data,
        "pot":        {"stars": total_stars, "donuts": total_donuts, "gifts": total_gifts},
        "last_game":  last_game,
        "best_game":  best_game,
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

    value_stars = _get_gift_value_stars(gift_id)

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
    """Инвентарь пользователя для выбора подарков в PvP с ценами в звёздах по курсу обмена."""
    tg_id  = current_user["id"]
    gifts  = await database.get_user_gifts(tg_id)
    result = []
    for gift_id, amount in gifts.items():
        info = _get_gift_info(gift_id)
        if info:
            raw_value = _get_gift_value_stars(gift_id)
            # Mirror the exchange-for-stars fallback formula so the displayed price
            # matches what the player would actually receive when exchanging the gift.
            # BASE_GIFTS  → stored value / 0.80  ≈ portal floor, then ×1.1
            # MAIN_GIFTS  → required_value / 1.20 ≈ portal floor, then ×1.1
            # TG_GIFTS    → required_value + 10 (fixed TG exchange bonus)
            if gift_id in config.TG_GIFTS:
                exchange_stars = raw_value + 10
            elif gift_id in config.BASE_GIFTS:
                exchange_stars = max(1, int(raw_value / 0.80 * 1.1))
            else:  # MAIN_GIFTS
                exchange_stars = max(1, int(raw_value / 1.20 * 1.1))
            result.append({
                "gift_id":       gift_id,
                "name":          info.get("name", ""),
                "photo":         info.get("photo", ""),
                "value_stars":   raw_value,
                "exchange_stars": exchange_stars,
                "amount":        amount,
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
