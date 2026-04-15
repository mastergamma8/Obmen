# db_init.py
# Инициализация базы данных: создание таблиц и безопасные миграции.
# Вызывается один раз при старте приложения.

import aiosqlite
from db.db_core import DB_NAME


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

        try: await db.execute("ALTER TABLE users ADD COLUMN notified_free_spin INTEGER DEFAULT 0")
        except Exception: pass

        try: await db.execute("ALTER TABLE users ADD COLUMN last_gift_withdraw INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_gift_withdraw INTEGER DEFAULT 1")
        except Exception: pass

        try: await db.execute("ALTER TABLE users ADD COLUMN last_gift_claim INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_gift_claim INTEGER DEFAULT 1")
        except Exception: pass

        try: await db.execute("ALTER TABLE users ADD COLUMN last_free_case INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN notified_free_case INTEGER DEFAULT 1")
        except Exception: pass

        # Метки времени последней отправки — для повторных уведомлений каждые 24ч
        try: await db.execute("ALTER TABLE users ADD COLUMN last_notified_free_spin INTEGER DEFAULT 0")
        except Exception: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN last_notified_free_case INTEGER DEFAULT 0")
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                reward_type TEXT NOT NULL,
                reward_value INTEGER NOT NULL DEFAULT 0,
                case_id INTEGER DEFAULT NULL,
                max_uses INTEGER NOT NULL DEFAULT 1,
                uses_left INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER DEFAULT NULL,
                created_at INTEGER NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                redeemed_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_promo_cases (
                user_id INTEGER NOT NULL,
                case_id INTEGER NOT NULL,
                amount INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, case_id)
            )
        """)

        await db.commit()


async def init_rocket_games_table():
    """Создаёт таблицу для хранения активных ракетных игр в БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rocket_active_games (
                user_id     INTEGER PRIMARY KEY,
                bet         INTEGER NOT NULL,
                currency    TEXT    NOT NULL DEFAULT 'donuts',
                crash_point REAL    NOT NULL,
                pool_amount INTEGER NOT NULL DEFAULT 0,
                created_at  INTEGER NOT NULL
            )
        """)
        await db.commit()
