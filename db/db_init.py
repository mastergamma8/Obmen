# db_init.py
# Инициализация базы данных: создание таблиц и безопасные миграции.
# Вызывается один раз при старте приложения.
#
# PostgreSQL-only. Используется ADD COLUMN IF NOT EXISTS вместо try/except,
# что корректно работает в транзакциях PostgreSQL (и не требует SAVEPOINT).

from db import db_async as aiosqlite
from db.db_core import DB_NAME


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Telegram user IDs могут превышать 2 147 483 647 (макс. для INTEGER).
        # Все колонки, хранящие tg_id / user_id / referrer_id, должны быть BIGINT.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id       BIGINT PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                photo_url   TEXT,
                balance     INTEGER DEFAULT 0,
                stars       INTEGER DEFAULT 0,
                referrer_id BIGINT  DEFAULT NULL,
                last_free_spin INTEGER DEFAULT 0
            )
        """)

        # Миграция типа для существующих баз (CREATE TABLE IF NOT EXISTS
        # не меняет типы уже существующих колонок).
        await db.execute("ALTER TABLE users ALTER COLUMN tg_id TYPE BIGINT")
        await db.execute("ALTER TABLE users ALTER COLUMN referrer_id TYPE BIGINT")

        # Безопасное добавление колонок для уже существующих баз.
        # ADD COLUMN IF NOT EXISTS поддерживается в PostgreSQL 9.6+
        # и не ломает транзакцию при повторном запуске в отличие от try/except.
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stars INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT DEFAULT NULL")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_free_spin INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notified_free_spin INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_gift_withdraw INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notified_gift_withdraw INTEGER DEFAULT 1")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_gift_claim INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notified_gift_claim INTEGER DEFAULT 1")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_free_case INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notified_free_case INTEGER DEFAULT 1")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_notified_free_spin INTEGER DEFAULT 0")
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_notified_free_case INTEGER DEFAULT 0")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_gifts (
                user_id BIGINT,
                gift_id INTEGER,
                amount  INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, gift_id)
            )
        """)
        await db.execute("ALTER TABLE user_gifts ALTER COLUMN user_id TYPE BIGINT")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_tasks (
                user_id BIGINT,
                task_id INTEGER,
                PRIMARY KEY (user_id, task_id)
            )
        """)
        await db.execute("ALTER TABLE user_tasks ALTER COLUMN user_id TYPE BIGINT")

        # id использует BIGSERIAL вместо INTEGER AUTOINCREMENT (SQLite-специфичный синтаксис).
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                id          BIGSERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                action_type TEXT   NOT NULL,
                description TEXT   NOT NULL,
                amount      INTEGER NOT NULL,
                created_at  INTEGER NOT NULL
            )
        """)
        await db.execute("ALTER TABLE user_history ALTER COLUMN user_id TYPE BIGINT")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code         TEXT    PRIMARY KEY,
                reward_type  TEXT    NOT NULL,
                reward_value INTEGER NOT NULL DEFAULT 0,
                case_id      INTEGER DEFAULT NULL,
                max_uses     INTEGER NOT NULL DEFAULT 1,
                uses_left    INTEGER NOT NULL DEFAULT 1,
                created_by   BIGINT  DEFAULT NULL,
                created_at   INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("ALTER TABLE promo_codes ALTER COLUMN created_by TYPE BIGINT")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                user_id     BIGINT  NOT NULL,
                code        TEXT    NOT NULL,
                redeemed_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, code)
            )
        """)
        await db.execute("ALTER TABLE promo_redemptions ALTER COLUMN user_id TYPE BIGINT")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_promo_cases (
                user_id BIGINT  NOT NULL,
                case_id INTEGER NOT NULL,
                amount  INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, case_id)
            )
        """)
        await db.execute("ALTER TABLE user_promo_cases ALTER COLUMN user_id TYPE BIGINT")

        await db.commit()


async def init_rocket_games_table():
    """Создаёт таблицу для хранения активных ракетных игр в БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rocket_active_games (
                user_id     BIGINT  PRIMARY KEY,
                bet         INTEGER NOT NULL,
                currency    TEXT    NOT NULL DEFAULT 'donuts',
                crash_point REAL    NOT NULL,
                pool_amount INTEGER NOT NULL DEFAULT 0,
                created_at  INTEGER NOT NULL
            )
        """)
        await db.execute("ALTER TABLE rocket_active_games ALTER COLUMN user_id TYPE BIGINT")
        await db.commit()
