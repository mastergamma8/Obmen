# routers/games_mines.py
# Эндпоинты игры «Мины». Валюта: только Stars (⭐).

import json
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
import database
from handlers.security import get_current_user
from db.db_history import log_action
from db.db_mines import (
    calc_mines_multiplier,
    mines_cashout_atomic,
    mines_get_game,
    mines_reveal_cell,
    mines_start_atomic,
)

router = APIRouter(prefix="/mines", tags=["mines"])
GRID   = 25  # 5×5


class MinesStartData(BaseModel):
    bet:         int = Field(..., gt=0)
    mines_count: int = Field(3, ge=1, le=23)


class MinesRevealData(BaseModel):
    cell: int = Field(..., ge=0, lt=GRID)


# ─────────────────────────────────────────────────────────────────────────────

@router.post("/start")
async def mines_start(data: MinesStartData, current_user: dict = Depends(get_current_user)):
    tg_id    = current_user["id"]
    cfg      = config.MINES_CONFIG
    min_b    = cfg["min_bet"]
    max_b    = cfg["max_bet"]

    if not (1 <= data.mines_count <= GRID - 2):
        raise HTTPException(400, "invalid_mines_count")
    if not (min_b <= data.bet <= max_b):
        raise HTTPException(400, f"bet_out_of_range:{min_b}:{max_b}")

    mine_cells = random.sample(range(GRID), data.mines_count)

    result = await mines_start_atomic(
        tg_id       = tg_id,
        bet         = data.bet,
        mines_count = data.mines_count,
        mine_cells  = mine_cells,
        house_edge  = cfg["house_edge"],
    )

    if not result["ok"]:
        code = 402 if result["reason"] == "insufficient_balance" else 400
        raise HTTPException(code, result["reason"])

    await log_action(
        user_id     = tg_id,
        action_type = "mines_bet",
        description = f"Мины: ставка {data.bet}⭐, {data.mines_count} мин",
        amount      = -data.bet,
    )

    user       = await database.get_user_data(tg_id)
    first_mult = calc_mines_multiplier(GRID, data.mines_count, 1, cfg["house_edge"])

    return {
        "ok":             True,
        "grid_size":      GRID,
        "mines_count":    data.mines_count,
        "bet":            data.bet,
        "next_multiplier": first_mult,
        "balance":        user.get("stars", 0),
    }


@router.post("/reveal")
async def mines_reveal(data: MinesRevealData, current_user: dict = Depends(get_current_user)):
    tg_id  = current_user["id"]
    result = await mines_reveal_cell(tg_id=tg_id, cell=data.cell)

    if not result["ok"]:
        raise HTTPException(400, result["reason"])

    if result["hit_mine"]:
        await log_action(
            user_id     = tg_id,
            action_type = "mines_lose",
            description = f"Мины: проигрыш {result['bet']}⭐",
            amount      = -result["bet"],
        )
        user = await database.get_user_data(tg_id)
        return {
            "ok":         True,
            "hit_mine":   True,
            "mine_cells": result["mine_cells"],
            "revealed":   result["revealed"],
            "balance":    user.get("stars", 0),
        }

    return {
        "ok":              True,
        "hit_mine":        False,
        "cell":            result["cell"],
        "revealed":        result["revealed"],
        "multiplier":      result["multiplier"],
        "next_multiplier": result.get("next_multiplier"),
        "safe_left":       result.get("safe_left"),
    }


@router.post("/cashout")
async def mines_cashout(current_user: dict = Depends(get_current_user)):
    tg_id  = current_user["id"]
    result = await mines_cashout_atomic(tg_id)

    if not result["ok"]:
        raise HTTPException(400, result["reason"])

    await log_action(
        user_id     = tg_id,
        action_type = "mines_win",
        description = f"Мины: выигрыш {result['win_amount']}⭐ (×{result['multiplier']})",
        amount      = result["win_amount"],
    )

    user = await database.get_user_data(tg_id)
    return {
        "ok":         True,
        "win_amount": result["win_amount"],
        "multiplier": result["multiplier"],
        "mine_cells": result["mine_cells"],
        "revealed":   result["revealed"],
        "balance":    user.get("stars", 0),
    }


@router.get("/state")
async def mines_state(current_user: dict = Depends(get_current_user)):
    """Восстановление сессии после переподключения."""
    tg_id = current_user["id"]
    game  = await mines_get_game(tg_id)
    if not game:
        return {"active": False}

    cfg      = config.MINES_CONFIG
    revealed = json.loads(game["revealed"])
    safe_left = game["grid_size"] - game["mines_count"] - len(revealed)
    next_mult = (
        calc_mines_multiplier(
            game["grid_size"], game["mines_count"],
            len(revealed) + 1, cfg["house_edge"],
        )
        if safe_left > 0 else None
    )

    return {
        "active":          True,
        "bet":             game["bet"],
        "mines_count":     game["mines_count"],
        "grid_size":       game["grid_size"],
        "revealed":        revealed,
        "multiplier":      game["multiplier"],
        "next_multiplier": next_mult,
        "safe_left":       safe_left,
    }
