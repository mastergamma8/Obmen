# db/db_mines.py
# Активные сессии игры «Мины» (Minesweeper Casino).
# Валюта: только Stars (⭐).

import json
import math
import time
from datetime import datetime, timezone
from db import db_async as aiosqlite
from db.db_core import DB_NAME


# ─────────────────────────────────────────────────────────────────────────────
# Расчёт множителя
# ─────────────────────────────────────────────────────────────────────────────

def calc_mines_multiplier(total: int, mines: int, revealed: int, house_edge: float) -> float:
    """
    Честный множитель после `revealed` безопасных открытий.

        P(k безопасных подряд) = ∏ (safe−i)/(total−i),  i = 0..k−1
        multiplier = (1 − house_edge) / P
    """
    if revealed <= 0:
        return 1.0
    safe = total - mines
    if safe <= 0 or revealed > safe:
        return 1.0
    prob = 1.0
    for i in range(revealed):
        prob *= (safe - i) / (total - i)
    if prob <= 0:
        return 1.0
    return round((1.0 - house_edge) / prob, 4)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Инициализация таблицы
# ─────────────────────────────────────────────────────────────────────────────

async def init_mines_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mines_active_games (
                user_id     BIGINT  PRIMARY KEY,
                bet         INTEGER NOT NULL,
                mines_count INTEGER NOT NULL DEFAULT 3,
                grid_size   INTEGER NOT NULL DEFAULT 25,
                mine_cells  TEXT    NOT NULL DEFAULT '[]',
                revealed    TEXT    NOT NULL DEFAULT '[]',
                multiplier  FLOAT8  NOT NULL DEFAULT 1.0,
                created_at  INTEGER NOT NULL
            )
        """)
        await db.execute(
            "ALTER TABLE mines_active_games ALTER COLUMN user_id TYPE BIGINT"
        )
        await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Чтение
# ─────────────────────────────────────────────────────────────────────────────

async def mines_get_game(tg_id: int) -> dict | None:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mines_active_games WHERE user_id = ?", (tg_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Старт — атомарно: списание + банк + запись игры
# ─────────────────────────────────────────────────────────────────────────────

async def mines_start_atomic(
    tg_id: int,
    bet: int,
    mines_count: int,
    mine_cells: list[int],
    house_edge: float,
) -> dict:
    """
    BEGIN IMMEDIATE — три шага атомарно:
      1. Списывает bet (stars) с пользователя.
      2. Обновляет банк и дневную статистику.
      3. Создаёт запись активной игры.

    Возвращает {"ok": True} или {"ok": False, "reason": str}.
    """
    now   = int(time.time())
    today = _today()
    edge  = math.ceil(bet * house_edge)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")

        # 1. Атомарное списание — только если хватает звёзд
        cur = await db.execute(
            "UPDATE users SET stars = stars - ? WHERE tg_id = ? AND stars >= ?",
            (bet, tg_id, bet),
        )
        if cur.rowcount != 1:
            await db.rollback()
            return {"ok": False, "reason": "insufficient_balance"}

        # 2. Банк: депозит и статистика
        await db.execute("""
            UPDATE system_bank SET
                stars_deposited        = stars_deposited + ?,
                total_deposited_value  = total_deposited_value + ?,
                total_house_edge_value = total_house_edge_value + ?,
                games_count            = games_count + 1,
                updated_at             = ?
            WHERE id = 1
        """, (bet, bet, edge, now))

        await db.execute("""
            INSERT INTO bank_day_stats
                (day_date, deposited_value, house_edge_value, games_count, stars_deposited)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(day_date) DO UPDATE SET
                deposited_value  = bank_day_stats.deposited_value  + excluded.deposited_value,
                house_edge_value = bank_day_stats.house_edge_value + excluded.house_edge_value,
                games_count      = bank_day_stats.games_count + 1,
                stars_deposited  = bank_day_stats.stars_deposited  + excluded.stars_deposited
        """, (today, bet, edge, bet))

        # 3. Удаляем старую сессию (если есть) и создаём новую
        await db.execute(
            "DELETE FROM mines_active_games WHERE user_id = ?", (tg_id,)
        )
        await db.execute("""
            INSERT INTO mines_active_games
                (user_id, bet, mines_count, grid_size, mine_cells, revealed, multiplier, created_at)
            VALUES (?, ?, ?, 25, ?, '[]', 1.0, ?)
        """, (tg_id, bet, mines_count, json.dumps(mine_cells), now))

        await db.commit()

    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# Открытие ячейки
# ─────────────────────────────────────────────────────────────────────────────

async def mines_reveal_cell(tg_id: int, cell: int) -> dict:
    """
    Открывает ячейку.
    — Мина → удаляет сессию, возвращает hit_mine=True.
    — Пусто → обновляет множитель, возвращает новое состояние.
    """
    import config as _cfg

    game = await mines_get_game(tg_id)
    if not game:
        return {"ok": False, "reason": "no_active_game"}

    mine_cells = json.loads(game["mine_cells"])
    revealed   = json.loads(game["revealed"])

    if cell in revealed:
        return {"ok": False, "reason": "already_revealed"}

    # ── Мина ─────────────────────────────────────────────────────────────────
    if cell in mine_cells:
        await _mines_delete(tg_id)
        return {
            "ok": True,
            "hit_mine": True,
            "mine_cells": mine_cells,
            "revealed":   revealed,
            "bet":        game["bet"],
        }

    # ── Безопасная ячейка ─────────────────────────────────────────────────────
    revealed.append(cell)
    he    = _cfg.MINES_CONFIG["house_edge"]
    total = game["grid_size"]
    mines = game["mines_count"]
    k     = len(revealed)

    new_mult  = calc_mines_multiplier(total, mines, k,     he)
    next_mult = calc_mines_multiplier(total, mines, k + 1, he)
    safe_left = total - mines - k

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE mines_active_games SET revealed = ?, multiplier = ? WHERE user_id = ?",
            (json.dumps(revealed), new_mult, tg_id),
        )
        await db.commit()

    return {
        "ok": True,
        "hit_mine":      False,
        "cell":          cell,
        "revealed":      revealed,
        "multiplier":    new_mult,
        "next_multiplier": next_mult if safe_left > 0 else None,
        "mines_count":   mines,
        "safe_left":     safe_left,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Кэшаут — атомарно: начисление + банк
# ─────────────────────────────────────────────────────────────────────────────

async def mines_cashout_atomic(tg_id: int) -> dict:
    """
    Завершает игру и атомарно зачисляет выигрыш в звёздах.
    Проверяет ликвидность банка.
    """
    import config as _cfg
    from db.db_bank import bank_get_max_payout

    game = await mines_get_game(tg_id)
    if not game:
        return {"ok": False, "reason": "no_active_game"}

    revealed = json.loads(game["revealed"])
    if not revealed:
        return {"ok": False, "reason": "no_reveals"}

    bet        = game["bet"]
    multiplier = game["multiplier"]
    now        = int(time.time())
    today      = _today()

    # Выигрыш в звёздах (целые числа)
    win_raw = bet * multiplier
    max_pay = await bank_get_max_payout()   # в звёздах (value единицы = 1 star)
    if win_raw > max_pay:
        win_raw    = max_pay
        multiplier = round(win_raw / bet, 4)

    win_amount = max(1, round(win_raw))
    mine_cells = json.loads(game["mine_cells"])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")

        await db.execute(
            "DELETE FROM mines_active_games WHERE user_id = ?", (tg_id,)
        )
        await db.execute(
            "UPDATE users SET stars = stars + ? WHERE tg_id = ?",
            (win_amount, tg_id),
        )
        await db.execute("""
            UPDATE system_bank SET
                stars_paid_out       = stars_paid_out + ?,
                total_paid_out_value = total_paid_out_value + ?,
                updated_at           = ?
            WHERE id = 1
        """, (win_amount, win_amount, now))

        await db.execute("""
            INSERT INTO bank_day_stats (day_date, paid_out_value, stars_paid_out)
            VALUES (?, ?, ?)
            ON CONFLICT(day_date) DO UPDATE SET
                paid_out_value = bank_day_stats.paid_out_value + excluded.paid_out_value,
                stars_paid_out = bank_day_stats.stars_paid_out + excluded.stars_paid_out
        """, (today, win_amount, win_amount))

        await db.commit()

    return {
        "ok":         True,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "mine_cells": mine_cells,
        "revealed":   revealed,
    }


async def _mines_delete(tg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM mines_active_games WHERE user_id = ?", (tg_id,)
        )
        await db.commit()
