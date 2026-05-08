# routers/games_mines.py
# =====================================================
# МИНЫ — ИНДИВИДУАЛЬНАЯ ИГРА ДЛЯ КАЖДОГО ИГРОКА
# =====================================================

import asyncio
import math
import random
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from handlers.security import get_current_user

router = APIRouter(prefix="/mines", tags=["mines"])

# ─────────────────────────────────────────────────────────────
# ПАРАМЕТРЫ
# ─────────────────────────────────────────────────────────────

HOUSE_EDGE   = 0.10
MIN_BET      = 50
MAX_BET      = 5000
GRID_SIZE    = 25   # 5×5
VALID_MINES  = {1, 3, 5, 10}

# ─────────────────────────────────────────────────────────────
# АКТИВНЫЕ ИГРЫ (user_id → game state)
# ─────────────────────────────────────────────────────────────

_games: Dict[int, Dict[str, Any]] = {}
_lock  = asyncio.Lock()


# ─────────────────────────────────────────────────────────────
# МАТЕМАТИКА: мультипликатор
# ─────────────────────────────────────────────────────────────

def _calc_multiplier(mines: int, revealed: int) -> float:
    """
    Справедливый мультипликатор после вскрытия `revealed` безопасных ячеек:
      mult = C(25, revealed) / C(25 - mines, revealed) × (1 - house_edge)

    При revealed=0 возвращает 1.00.
    """
    if revealed == 0:
        return 1.00
    safe = GRID_SIZE - mines
    if revealed > safe:
        return 1.00
    # Вычисляем C(25, k) / C(25-m, k) без overflow через пошаговое умножение
    num, den = 1, 1
    for i in range(revealed):
        num *= (GRID_SIZE - i)
        den *= (safe - i)
    raw = num / den
    return round(raw * (1.0 - HOUSE_EDGE), 4)


def _next_multiplier(mines: int, revealed: int) -> float:
    """Мультипликатор если откроем ещё одну безопасную ячейку."""
    return _calc_multiplier(mines, revealed + 1)


# ─────────────────────────────────────────────────────────────
# СХЕМЫ
# ─────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    bet:   int
    mines: int


class RevealRequest(BaseModel):
    cell: int   # 0-24


# ─────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ
# ─────────────────────────────────────────────────────────────

@router.post("/start")
async def mines_start(req: StartRequest, user_id: int = Depends(get_current_user)):
    """Начать новую игру. Списывает ставку и генерирует поле."""
    if req.mines not in VALID_MINES:
        raise HTTPException(400, f"Недопустимое число мин. Выберите: {sorted(VALID_MINES)}")
    if not (MIN_BET <= req.bet <= MAX_BET):
        raise HTTPException(400, f"Ставка должна быть от {MIN_BET} до {MAX_BET} звёзд")

    async with _lock:
        # Если у игрока уже есть активная игра — отменяем без возврата
        if user_id in _games:
            del _games[user_id]

    # Списываем ставку (атомарно через банк)
    ok = await database.deduct_and_deposit_atomic(
        user_id=user_id,
        gross_bet=req.bet,
        house_edge=HOUSE_EDGE,
        asset_type="stars",
    )
    if ok is None:
        raise HTTPException(400, "Недостаточно звёзд или ошибка списания")

    # Генерируем позиции мин (набор индексов 0-24)
    mine_positions = set(random.sample(range(GRID_SIZE), req.mines))

    async with _lock:
        _games[user_id] = {
            "bet":       req.bet,
            "mines":     req.mines,
            "mine_pos":  mine_positions,
            "revealed":  [],        # список вскрытых безопасных ячеек
            "status":    "active",  # active | won | lost
            "started":   time.time(),
        }

    return {
        "ok":            True,
        "bet":           req.bet,
        "mines":         req.mines,
        "multiplier":    1.00,
        "next_mult":     _next_multiplier(req.mines, 0),
        "win_amount":    req.bet,
    }


@router.post("/reveal")
async def mines_reveal(req: RevealRequest, user_id: int = Depends(get_current_user)):
    """Открыть ячейку. Возвращает результат и текущий выигрыш."""
    if not (0 <= req.cell < GRID_SIZE):
        raise HTTPException(400, "Недопустимый индекс ячейки")

    async with _lock:
        game = _games.get(user_id)

    if not game or game["status"] != "active":
        raise HTTPException(400, "Нет активной игры")

    if req.cell in game["revealed"]:
        raise HTTPException(400, "Ячейка уже открыта")

    is_mine = req.cell in game["mine_pos"]

    if is_mine:
        async with _lock:
            _games[user_id]["status"] = "lost"
            mine_positions = list(_games[user_id]["mine_pos"])
            revealed       = list(_games[user_id]["revealed"])
        # Записываем проигрыш в историю
        await database.add_history_entry(
            user_id, "mines_lose",
            f"Мины — проигрыш ({game['mines']} мин)",
            -game["bet"],
        )
        return {
            "ok":           True,
            "hit_mine":     True,
            "cell":         req.cell,
            "mine_pos":     mine_positions,
            "revealed":     revealed,
            "multiplier":   0.00,
            "win_amount":   0,
            "status":       "lost",
        }

    # Безопасная ячейка — обновляем состояние
    async with _lock:
        _games[user_id]["revealed"].append(req.cell)
        revealed  = list(_games[user_id]["revealed"])
        mines     = _games[user_id]["mines"]
        bet       = _games[user_id]["bet"]
        safe_left = (GRID_SIZE - mines) - len(revealed)

    mult       = _calc_multiplier(mines, len(revealed))
    win_amount = int(bet * mult)
    next_mult  = _next_multiplier(mines, len(revealed)) if safe_left > 0 else None

    # Если открыты все безопасные ячейки — автовыигрыш
    if safe_left == 0:
        async with _lock:
            _games[user_id]["status"] = "won"
        profit = win_amount - bet
        if profit > 0:
            await database.bank_payout(profit, asset_type="stars")
        await database.add_stars_to_user(user_id, win_amount)
        await database.add_history_entry(
            user_id, "mines_win",
            f"Мины (x{mult:.2f})",
            profit,
        )
        return {
            "ok":           True,
            "hit_mine":     False,
            "cell":         req.cell,
            "revealed":     revealed,
            "multiplier":   mult,
            "win_amount":   win_amount,
            "next_mult":    None,
            "status":       "won",
            "auto_cashout": True,
        }

    return {
        "ok":         True,
        "hit_mine":   False,
        "cell":       req.cell,
        "revealed":   revealed,
        "multiplier": mult,
        "win_amount": win_amount,
        "next_mult":  next_mult,
        "status":     "active",
    }


@router.post("/cashout")
async def mines_cashout(user_id: int = Depends(get_current_user)):
    """Забрать выигрыш вручную."""
    async with _lock:
        game = _games.get(user_id)

    if not game or game["status"] != "active":
        raise HTTPException(400, "Нет активной игры для вывода")

    revealed  = game["revealed"]
    mines     = game["mines"]
    bet       = game["bet"]

    if len(revealed) == 0:
        raise HTTPException(400, "Откройте хотя бы одну ячейку перед выводом")

    mult       = _calc_multiplier(mines, len(revealed))
    win_amount = int(bet * mult)
    profit     = win_amount - bet

    async with _lock:
        _games[user_id]["status"] = "won"

    if profit > 0:
        await database.bank_payout(profit, asset_type="stars")
    await database.add_stars_to_user(user_id, win_amount)
    await database.add_history_entry(
        user_id, "mines_win",
        f"Мины (x{mult:.2f})",
        profit,
    )

    return {
        "ok":         True,
        "multiplier": mult,
        "win_amount": win_amount,
        "profit":     profit,
    }


@router.post("/cancel")
async def mines_cancel(user_id: int = Depends(get_current_user)):
    """Отменить игру до первого хода (возврат ставки)."""
    async with _lock:
        game = _games.get(user_id)

    if not game or game["status"] != "active":
        raise HTTPException(400, "Нет активной игры для отмены")

    if len(game["revealed"]) > 0:
        raise HTTPException(400, "Нельзя отменить игру после первого хода")

    async with _lock:
        del _games[user_id]

    # Возвращаем ставку: выплачиваем из банка (bank_payout не вычтет house_edge снова)
    # Фактически возврат: добавляем ставку обратно пользователю
    await database.add_stars_to_user(user_id, game["bet"])
    # Возмещаем банку: снимаем то что он получил (net = bet*(1-HE))
    # Для простоты — просто отдаём ставку игроку, банк уже получил HE
    # Можно сделать полный возврат через bank_payout:
    try:
        net = int(game["bet"] * (1.0 - HOUSE_EDGE))
        await database.bank_payout(net, asset_type="stars")
    except Exception:
        pass

    return {"ok": True, "refunded": game["bet"]}


@router.get("/state")
async def mines_state(user_id: int = Depends(get_current_user)):
    """Возвращает текущее состояние активной игры (если есть)."""
    async with _lock:
        game = _games.get(user_id)

    if not game:
        return {"active": False}

    revealed   = game["revealed"]
    mines      = game["mines"]
    bet        = game["bet"]
    mult       = _calc_multiplier(mines, len(revealed))
    win_amount = int(bet * mult)
    safe_left  = (GRID_SIZE - mines) - len(revealed)
    next_mult  = _next_multiplier(mines, len(revealed)) if safe_left > 0 else None

    return {
        "active":      True,
        "bet":         bet,
        "mines":       mines,
        "revealed":    revealed,
        "multiplier":  mult,
        "win_amount":  win_amount,
        "next_mult":   next_mult,
        "status":      game["status"],
            }
