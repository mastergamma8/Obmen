# db_users.py
# Пользователи: регистрация, профиль, баланс, подарки, кулдауны рулетки/кейса/вывода.

import aiosqlite
from db_core import DB_NAME, GIFT_CLAIM_COOLDOWN, GIFT_WITHDRAW_COOLDOWN


# ==========================================
# ОСНОВНЫЕ ФУНКЦИИ ПОЛЬЗОВАТЕЛЕЙ
# ==========================================

async def upsert_user(tg_id: int, username: str, first_name: str, photo_url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (
                tg_id, username, first_name, photo_url,
                balance, stars, last_free_spin, notified_free_spin,
                last_gift_withdraw, notified_gift_withdraw,
                last_gift_claim, notified_gift_claim,
                last_free_case, notified_free_case
            )
            VALUES (?, ?, ?, ?, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1)
            ON CONFLICT(tg_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                photo_url=excluded.photo_url
        """, (tg_id, username, first_name, photo_url))
        await db.commit()

async def get_user_profile(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT username, first_name FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {"username": "", "first_name": ""}

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT balance, stars, last_free_spin, last_free_case FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {"balance": 0, "stars": 0, "last_free_spin": 0, "last_free_case": 0}

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT tg_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


# ==========================================
# БАЛАНС И ЗВЁЗДЫ
# ==========================================

async def add_points_to_user(user_id: int, points: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE tg_id = ?", (points, user_id)
        )
        await db.commit()

async def add_stars_to_user(user_id: int, stars: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET stars = stars + ? WHERE tg_id = ?", (stars, user_id)
        )
        await db.commit()

async def deduct_stars(tg_id: int, amount: int) -> bool:
    """Списывает звёзды с баланса пользователя, если их достаточно."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT stars FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return False
        await db.execute("UPDATE users SET stars = stars - ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()
        return True


# ==========================================
# РУЛЕТКА — ТАЙМЕР И УВЕДОМЛЕНИЯ
# ==========================================

async def update_last_free_spin(user_id: int, timestamp: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_free_spin = ?, notified_free_spin = 0 WHERE tg_id = ?",
            (timestamp, user_id)
        )
        await db.commit()

async def get_users_to_notify(current_timestamp: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT tg_id FROM users
            WHERE (? - last_free_spin) >= 86400
              AND notified_free_spin = 0
        """, (current_timestamp,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_user_notified(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET notified_free_spin = 1 WHERE tg_id = ?", (user_id,)
        )
        await db.commit()


# ==========================================
# БЕСПЛАТНЫЙ КЕЙС — ТАЙМЕР (24 ч)
# ==========================================

async def get_last_free_case(user_id: int) -> int:
    """Возвращает timestamp последнего открытия бесплатного кейса."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT last_free_case FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_last_free_case(user_id: int, timestamp: int):
    """Сохраняет время открытия бесплатного кейса и сбрасывает флаг уведомления."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_free_case = ?, notified_free_case = 0 WHERE tg_id = ?",
            (timestamp, user_id)
        )
        await db.commit()

async def get_users_to_notify_free_case(current_timestamp: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT tg_id FROM users
            WHERE last_free_case > 0
              AND (? - last_free_case) >= 86400
              AND notified_free_case = 0
        """, (current_timestamp,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_user_notified_free_case(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET notified_free_case = 1 WHERE tg_id = ?", (user_id,)
        )
        await db.commit()


# ==========================================
# ЛИМИТ ПОКУПКИ ПОДАРКОВ — ГЛАВНАЯ СТРАНИЦА
# ==========================================

async def claim_main_gift(user_id: int, gift_id: int, cost: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT balance FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < cost:
                return False
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE tg_id = ?", (cost, user_id)
        )
        await db.execute("""
            INSERT INTO user_gifts (user_id, gift_id, amount)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, gift_id) DO UPDATE SET amount = amount + 1
        """, (user_id, gift_id))
        await db.commit()
        return True

async def get_last_gift_claim(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT last_gift_claim FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_last_gift_claim(user_id: int, timestamp: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_gift_claim = ?, notified_gift_claim = 0 WHERE tg_id = ?",
            (timestamp, user_id)
        )
        await db.commit()

async def get_users_to_notify_gift_claim(current_timestamp: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT tg_id FROM users
            WHERE last_gift_claim > 0
              AND (? - last_gift_claim) >= ?
              AND notified_gift_claim = 0
        """, (current_timestamp, GIFT_CLAIM_COOLDOWN)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_user_notified_gift_claim(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET notified_gift_claim = 1 WHERE tg_id = ?", (user_id,)
        )
        await db.commit()


# ==========================================
# ЛИМИТ ВЫВОДА ПОДАРКОВ — ИНВЕНТАРЬ
# ==========================================

async def get_last_gift_withdraw(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT last_gift_withdraw FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_last_gift_withdraw(user_id: int, timestamp: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_gift_withdraw = ?, notified_gift_withdraw = 0 WHERE tg_id = ?",
            (timestamp, user_id)
        )
        await db.commit()

async def get_users_to_notify_gift_withdraw(current_timestamp: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT tg_id FROM users
            WHERE last_gift_withdraw > 0
              AND (? - last_gift_withdraw) >= ?
              AND notified_gift_withdraw = 0
        """, (current_timestamp, GIFT_WITHDRAW_COOLDOWN)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_user_notified_gift_withdraw(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET notified_gift_withdraw = 1 WHERE tg_id = ?", (user_id,)
        )
        await db.commit()


# ==========================================
# ПОДАРКИ ПОЛЬЗОВАТЕЛЕЙ
# ==========================================

async def add_gift_to_user(user_id: int, gift_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_gifts (user_id, gift_id, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, gift_id) DO UPDATE SET amount = amount + excluded.amount
        """, (user_id, gift_id, amount))
        await db.commit()

async def remove_gift_from_user(user_id: int, gift_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE user_gifts SET amount = amount - 1
            WHERE user_id = ? AND gift_id = ? AND amount > 0
        """, (user_id, gift_id))
        await db.commit()
        return True

async def get_user_gifts(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT gift_id, amount FROM user_gifts WHERE user_id = ? AND amount > 0", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row["gift_id"]: row["amount"] for row in rows}
