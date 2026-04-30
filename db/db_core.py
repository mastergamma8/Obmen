# db_core.py
# Общие константы подключения к базе данных.
# Импортируется всеми остальными db_*.py модулями.

import os

from db import db_async as aiosqlite  # noqa: F401 — совместимый API для SQLite/PostgreSQL

# Railway / локальная разработка:
# - DATABASE_URL / POSTGRES_URL / RAILWAY_DATABASE_URL -> PostgreSQL
# - иначе локальный файл SQLite для разработки
DB_NAME = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("RAILWAY_DATABASE_URL")
    or "database.db"
)

GIFT_WITHDRAW_COOLDOWN = 5 * 3600  # 5 часов — лимит вывода (инвентарь)
GIFT_CLAIM_COOLDOWN   = 5 * 3600  # 5 часов — лимит покупки (главная)
