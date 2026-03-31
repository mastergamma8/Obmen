# db_rocket.py
# Хранение активных ракетных игр в БД вместо памяти.

import time
import aiosqlite
from db.db_core import DB_NAME


async def rocket_start_game(user_id: int, bet: int, currency: str,
                             crash_point: float, pool_amount: int) -> bool:
    """Создаёт запись об активной игре. Возвращает False если игра уже есть."""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("""
                INSERT INTO rocket_active_games
                    (user_id, bet, currency, crash_point, pool_amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, bet, currency, crash_point, pool_amount, int(time.time())))
            await db.commit()
            return True
        except Exception:
            return False


async def rocket_get_game(user_id: int) -> dict | None:
    """Возвращает активную игру пользователя или None."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM rocket_active_games WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def rocket_end_game(user_id: int) -> dict | None:
    """
    Атомарно удаляет активную игру через DELETE ... RETURNING,
    исключая гонку между двумя одновременными запросами cashout/crash.
    Возвращает данные игры или None если игры не было.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute(
            "DELETE FROM rocket_active_games WHERE user_id = ? RETURNING *",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        await db.commit()
        return dict(row) if row else None


async def rocket_start_atomic(
    user_id: int,
    bet: int,
    currency: str,
    crash_point: float,
    house_edge: float,
) -> dict:
    """
    Выполняет все три шага старта игры в одной транзакции BEGIN IMMEDIATE:
      1. Списание ставки с баланса пользователя (deduct).
      2. Зачисление ставки в банк (bank deposit).
      3. Создание записи активной игры.

    Возвращает словарь:
      {"ok": True,  "pool_amount": int}   — успех
      {"ok": False, "reason": str}        — одна из трёх операций не прошла

    Если шаг 3 падает после шагов 1–2, транзакция откатывается целиком,
    деньги и банк остаются нетронутыми.
    """
    import config as _cfg

    house_edge_amount = int(bet * house_edge)
    pool_amount       = bet - house_edge_amount
    rate              = _cfg.DONUTS_TO_STARS_RATE

    if currency == "donuts":
        balance_col   = "donuts_balance"
        deposited_col = "donuts_deposited"
        user_col      = "balance"
        bet_value     = bet         * rate
        edge_value    = house_edge_amount * rate
    else:  # stars
        balance_col   = "stars_balance"
        deposited_col = "stars_deposited"
        user_col      = "stars"
        bet_value     = bet
        edge_value    = house_edge_amount

    now = int(time.time())

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")

        # Шаг 1: списание у пользователя (атомарное — WHERE balance >= bet)
        cur = await db.execute(
            f"UPDATE users SET {user_col} = {user_col} - ? "
            f"WHERE tg_id = ? AND {user_col} >= ?",
            (bet, user_id, bet),
        )
        if cur.rowcount != 1:
            await db.rollback()
            return {"ok": False, "reason": "insufficient_balance"}

        # Шаг 2: пополнение банка
        await db.execute(f"""
            UPDATE system_bank SET
                {balance_col}          = {balance_col} + ?,
                {deposited_col}        = {deposited_col} + ?,
                total_deposited_value  = total_deposited_value + ?,
                total_house_edge_value = total_house_edge_value + ?,
                updated_at             = ?
            WHERE id = 1
        """, (pool_amount, bet, bet_value, edge_value, now))

        # Шаг 3: создание записи активной игры
        try:
            await db.execute("""
                INSERT INTO rocket_active_games
                    (user_id, bet, currency, crash_point, pool_amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, bet, currency, crash_point, pool_amount, now))
        except Exception:
            # UNIQUE constraint — игра уже существует
            await db.rollback()
            return {"ok": False, "reason": "game_already_exists"}

        await db.commit()

    return {"ok": True, "pool_amount": pool_amount}
