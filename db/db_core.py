# db_core.py
# Общие константы подключения к базе данных.
# Импортируется всеми остальными db_*.py модулями.

import aiosqlite  # noqa: F401 — реэкспорт для удобства

DB_NAME = "database.db"

GIFT_WITHDRAW_COOLDOWN = 5 * 3600  # 5 часов — лимит вывода (инвентарь)
GIFT_CLAIM_COOLDOWN   = 5 * 3600  # 5 часов — лимит покупки (главная)
