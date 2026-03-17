# database.py
import aiosqlite

DB_NAME = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                photo_url TEXT,
                balance INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT NULL,
                last_free_spin INTEGER DEFAULT 0
            )
        """)
        # Безопасное добавление колонок, если база уже существует
        try: await db.execute("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0")
        except Exception: pass
        
        try: await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT NULL")
        except Exception: pass
        
        try: await db.execute("ALTER TABLE users ADD COLUMN last_free_spin INTEGER DEFAULT 0")
        except Exception: pass

        # Новая колонка для отслеживания отправки напоминания
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_free_spin INTEGER DEFAULT 0")
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

async def upsert_user(tg_id: int, username: str, first_name: str, photo_url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        # Для новых пользователей ставим notified_free_spin = 1, чтобы они не получали 
        # напоминание сразу же при регистрации (получат только после первой своей прокрутки)
        await db.execute("""
            INSERT INTO users (tg_id, username, first_name, photo_url, balance, last_free_spin, notified_free_spin)
            VALUES (?, ?, ?, ?, 0, 0, 1)
            ON CONFLICT(tg_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                photo_url=excluded.photo_url
        """, (tg_id, username, first_name, photo_url))
        await db.commit()

async def get_user_profile(user_id: int):
    """Возвращает профиль (имя и юзернейм) пользователя для уведомлений"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT username, first_name FROM users WHERE tg_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {"username": "", "first_name": ""}

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
        async with db.execute("SELECT referrer_id FROM users WHERE tg_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_referrals(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT first_name, photo_url FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def add_points_to_user(user_id: int, points: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET balance = balance + ? WHERE tg_id = ?
        """, (points, user_id))
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT balance, last_free_spin FROM users WHERE tg_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {"balance": 0, "last_free_spin": 0}

async def update_last_free_spin(user_id: int, timestamp: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # Сбрасываем флаг уведомления при использовании бесплатной прокрутки
        await db.execute("UPDATE users SET last_free_spin = ?, notified_free_spin = 0 WHERE tg_id = ?", (timestamp, user_id))
        await db.commit()

async def get_users_to_notify(current_timestamp: int):
    """Возвращает список ID пользователей, которым пора отправить напоминание"""
    async with aiosqlite.connect(DB_NAME) as db:
        # 86400 секунд = 24 часа
        async with db.execute("""
            SELECT tg_id FROM users 
            WHERE (? - last_free_spin) >= 86400 
            AND notified_free_spin = 0
        """, (current_timestamp,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_user_notified(user_id: int):
    """Отмечает, что пользователю отправлено напоминание"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET notified_free_spin = 1 WHERE tg_id = ?", (user_id,))
        await db.commit()

async def add_gift_to_user(user_id: int, gift_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_gifts (user_id, gift_id, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, gift_id) DO UPDATE SET
                amount = amount + excluded.amount
        """, (user_id, gift_id, amount))
        await db.commit()

async def remove_gift_from_user(user_id: int, gift_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE user_gifts 
            SET amount = amount - 1 
            WHERE user_id = ? AND gift_id = ? AND amount > 0
        """, (user_id, gift_id))
        await db.commit()

async def claim_main_gift(user_id: int, gift_id: int, cost: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE tg_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < cost:
                return False
        await db.execute("UPDATE users SET balance = balance - ? WHERE tg_id = ?", (cost, user_id))
        await db.execute("""
            INSERT INTO user_gifts (user_id, gift_id, amount)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, gift_id) DO UPDATE SET amount = amount + 1
        """, (user_id, gift_id))
        await db.commit()
        return True

async def get_user_gifts(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT gift_id, amount FROM user_gifts WHERE user_id = ? AND amount > 0", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row["gift_id"]: row["amount"] for row in rows}

async def get_completed_tasks(user_id: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def mark_task_completed(user_id: int, task_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO user_tasks (user_id, task_id) VALUES (?, ?)", (user_id, task_id))
        await db.commit()

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT tg_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_history_entry(user_id: int, action_type: str, description: str, amount: int):
    import time
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_history (user_id, action_type, description, amount, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action_type, description, amount, int(time.time())))
        await db.commit()

async def get_user_history(user_id: int, limit: int = 50):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, action_type, description, amount, created_at
            FROM user_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT tg_id, username, first_name, photo_url, balance as total_gifts FROM users ORDER BY balance DESC LIMIT 50"
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]