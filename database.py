# database.py
import aiosqlite

DB_NAME = "database.db"

GIFT_WITHDRAW_COOLDOWN = 5 * 3600  # 5 часов — лимит вывода (инвентарь)
GIFT_CLAIM_COOLDOWN   = 5 * 3600  # 5 часов — лимит покупки (главная)

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                photo_url TEXT,
                balance INTEGER DEFAULT 0,
                stars INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT NULL,
                last_free_spin INTEGER DEFAULT 0
            )
        """)
        # Безопасное добавление колонок, если база уже существует
        try: await db.execute("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0")
        except Exception: pass

        try: await db.execute("ALTER TABLE users ADD COLUMN stars INTEGER DEFAULT 0")
        except Exception: pass

        try: await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT NULL")
        except Exception: pass

        try: await db.execute("ALTER TABLE users ADD COLUMN last_free_spin INTEGER DEFAULT 0")
        except Exception: pass

        # Уведомление о доступности рулетки
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_free_spin INTEGER DEFAULT 0")
        except Exception: pass

        # Лимит вывода подарков (инвентарь / профиль)
        try: await db.execute("ALTER TABLE users ADD COLUMN last_gift_withdraw INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_gift_withdraw INTEGER DEFAULT 1")
        except Exception: pass

        # Лимит покупки подарков (главная страница)
        try: await db.execute("ALTER TABLE users ADD COLUMN last_gift_claim INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_gift_claim INTEGER DEFAULT 1")
        except Exception: pass

        # ── FREE CASE — кулдаун 24 ч ──────────────────────────────────────────
        try: await db.execute("ALTER TABLE users ADD COLUMN last_free_case INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_free_case INTEGER DEFAULT 1")
        except Exception: pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_gifts (
                user_id INTEGER,
                gift_id INTEGER,
                amount INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, gift_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_tasks (
                user_id INTEGER,
                task_id INTEGER,
                PRIMARY KEY (user_id, task_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                amount INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        await db.commit()


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
    """Возвращает ID пользователей, у которых прошло 24 ч с последнего открытия
    бесплатного кейса и уведомление ещё не отправлено."""
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
    """Помечает, что уведомление о бесплатном кейсе отправлено."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET notified_free_case = 1 WHERE tg_id = ?", (user_id,)
        )
        await db.commit()


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
        
# ==========================================
# ЛИМИТ ПОКУПКИ ПОДАРКОВ — ГЛАВНАЯ СТРАНИЦА
# ==========================================

async def get_last_gift_claim(user_id: int) -> int:
    """Возвращает timestamp последней покупки подарка на главной."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT last_gift_claim FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_last_gift_claim(user_id: int, timestamp: int):
    """Сохраняет время покупки и сбрасывает флаг уведомления."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_gift_claim = ?, notified_gift_claim = 0 WHERE tg_id = ?",
            (timestamp, user_id)
        )
        await db.commit()

async def get_users_to_notify_gift_claim(current_timestamp: int) -> list[int]:
    """Возвращает ID пользователей, у которых прошло 5 ч с последней покупки
    и уведомление ещё не отправлено."""
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
            # Ключи — int, чтобы совпадать с типом gift_id из config
            return {row["gift_id"]: row["amount"] for row in rows}


# ==========================================
# ЗАДАНИЯ
# ==========================================

async def get_completed_tasks(user_id: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_task_completed(user_id: int, task_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_tasks (user_id, task_id) VALUES (?, ?)",
            (user_id, task_id)
        )
        await db.commit()


# ==========================================
# ИСТОРИЯ ДЕЙСТВИЙ
# ==========================================

async def add_history_entry(user_id: int, action_type: str, description: str, amount: int):
    import time
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_history (user_id, action_type, description, amount, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action_type, description, amount, int(time.time())))
        await db.commit()

# Алиас для gifts.py — одинаковое поведение, удобное имя
async def log_action(user_id: int, action_type: str, description: str, amount: int):
    """Алиас add_history_entry, используется в gifts.py."""
    await add_history_entry(user_id, action_type, description, amount)

async def get_user_history(user_id: int, limit: int = 30, offset: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, action_type, description, amount, created_at
            FROM user_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_history_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_history WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ==========================================
# РЕФЕРАЛЫ
# ==========================================

async def set_referrer(user_id: int, referrer_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        if user_id != referrer_id:
            await db.execute("""
                UPDATE users SET referrer_id = ?
                WHERE tg_id = ? AND referrer_id IS NULL
            """, (referrer_id, user_id))
            await db.commit()

async def get_referrer(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT referrer_id FROM users WHERE tg_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_referrals(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT first_name, photo_url FROM users WHERE referrer_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def distribute_referral_bonus(user_id: int, gift_value: int):
    """Начисляет реферальный бонус пригласившему пользователю.

    Бонус = 10% от стоимости подарка. Если реферера нет — ничего не происходит.
    """
    referrer_id = await get_referrer(user_id)
    if not referrer_id:
        return
    bonus = max(1, int(gift_value * 0.10))
    await add_points_to_user(referrer_id, bonus)
    await add_history_entry(
        referrer_id,
        "referral_bonus",
        f"Реферальный бонус за покупку подарка рефералом (ID {user_id})",
        bonus
    )


# ==========================================
# ТАБЛИЦЫ ЛИДЕРОВ
# ==========================================

async def get_leaderboard():
    """Богачи: топ по балансу пончиков."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT tg_id, username, first_name, photo_url, balance AS total_gifts
            FROM users
            ORDER BY balance DESC
            LIMIT 50
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_rocket_leaderboard():
    """Сорвиголовы: топ по максимальному множителю ракеты за 7 дней."""
    import time
    import re
    week_ago = int(time.time()) - 7 * 86400
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT h.user_id, h.description,
                   u.first_name, u.photo_url, u.username
            FROM user_history h
            JOIN users u ON u.tg_id = h.user_id
            WHERE h.action_type LIKE 'rocket_win_%'
              AND h.created_at >= ?
        """, (week_ago,)) as cursor:
            rows = await cursor.fetchall()

    best: dict[int, dict] = {}
    multiplier_re = re.compile(r'x([\d.]+)')
    for row in rows:
        m = multiplier_re.search(row["description"])
        if not m:
            continue
        mult = float(m.group(1))
        uid = row["user_id"]
        if uid not in best or mult > best[uid]["max_multiplier"]:
            best[uid] = {
                "tg_id": uid,
                "first_name": row["first_name"],
                "photo_url": row["photo_url"],
                "username": row["username"],
                "max_multiplier": mult,
            }

    return sorted(best.values(), key=lambda x: x["max_multiplier"], reverse=True)[:50]

async def deduct_stars(tg_id: int, amount: int) -> bool:
    """Списывает звезды с баланса пользователя, если их достаточно."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT stars FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return False # Недостаточно звезд
        
        await db.execute("UPDATE users SET stars = stars - ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()
        return True

async def get_lucky_leaderboard():
    """Счастливчики: топ по лучшему одиночному результату из кейса."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT h.user_id, MAX(h.amount) AS best_ratio_x100,
                   u.first_name, u.photo_url, u.username
            FROM user_history h
            JOIN users u ON u.tg_id = h.user_id
            WHERE h.action_type = 'case_lucky_ratio'
            GROUP BY h.user_id
            ORDER BY best_ratio_x100 DESC
            LIMIT 50
        """) as cursor:
            rows = await cursor.fetchall()

    return [{
        "tg_id": row["user_id"],
        "first_name": row["first_name"],
        "photo_url": row["photo_url"],
        "username": row["username"],
        "ratio": row["best_ratio_x100"] / 100,
    } for row in rows]