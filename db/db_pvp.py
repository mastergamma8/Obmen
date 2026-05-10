# db_pvp.py
# Персистентное хранение состояния раундов PvP в БД.
# Обеспечивает сохранение round_id, last_game и best_game между деплоями.

import json
import time

from db import db_async as aiosqlite
from db.db_core import DB_NAME


async def load_pvp_round_state() -> dict:
    """Загружает сохранённое состояние PvP-раунда из БД.
    Возвращает словарь {round_id, last_game, best_game} или значения по умолчанию."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT round_id, last_game, best_game FROM game_round_state WHERE game = 'pvp'"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "round_id":  row["round_id"] or 0,
                        "last_game": json.loads(row["last_game"]) if row["last_game"] else None,
                        "best_game": json.loads(row["best_game"]) if row["best_game"] else None,
                    }
    except Exception as e:
        print(f"[PvP] load_pvp_round_state error: {e}")
    return {"round_id": 0, "last_game": None, "best_game": None}


async def save_pvp_round_state(round_id: int, last_game, best_game) -> None:
    """Сохраняет состояние PvP-раунда в БД (upsert)."""
    try:
        last_json = json.dumps(last_game) if last_game is not None else None
        best_json = json.dumps(best_game) if best_game is not None else None
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT INTO game_round_state (game, round_id, last_game, best_game, updated_at)
                VALUES ('pvp', $1, $2, $3, $4)
                ON CONFLICT (game) DO UPDATE SET
                    round_id   = EXCLUDED.round_id,
                    last_game  = EXCLUDED.last_game,
                    best_game  = EXCLUDED.best_game,
                    updated_at = EXCLUDED.updated_at
            """, (round_id, last_json, best_json, int(time.time())))
            await db.commit()
    except Exception as e:
        print(f"[PvP] save_pvp_round_state error: {e}")


async def load_rocket_round_id() -> int:
    """Загружает последний round_id ракеты из БД."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT round_id FROM game_round_state WHERE game = 'rocket'"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row["round_id"] or 0
    except Exception as e:
        print(f"[Rocket] load_rocket_round_id error: {e}")
    return 0


async def save_rocket_round_id(round_id: int) -> None:
    """Сохраняет текущий round_id ракеты в БД (upsert)."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT INTO game_round_state (game, round_id, updated_at)
                VALUES ('rocket', $1, $2)
                ON CONFLICT (game) DO UPDATE SET
                    round_id   = EXCLUDED.round_id,
                    updated_at = EXCLUDED.updated_at
            """, (round_id, int(time.time())))
            await db.commit()
    except Exception as e:
        print(f"[Rocket] save_rocket_round_id error: {e}")
