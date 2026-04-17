# db/db_settings.py
# Хранит глобальные настройки приложения в SQLite-таблице app_settings.
# Оба процесса (бот и FastAPI) читают и пишут через эти функции,
# поэтому изменения от бота мгновенно видны FastAPI — и наоборот.
#
# Схема:  key TEXT PRIMARY KEY, value TEXT
#
# Ключи:
#   maintenance_mode      — "1" / "0"
#   feature_flag_roulette — "1" / "0"
#   feature_flag_cases    — "1" / "0"
#   feature_flag_rocket   — "1" / "0"
#   feature_flag_limited_gifts — "1" / "0"
#   feature_flag_case_<id>     — "1" / "0"  (для конкретного кейса)

import aiosqlite
from db.db_core import DB_NAME

# ── Инициализация ──────────────────────────────────────────────────────────────

async def init_settings_table():
    """Создаёт таблицу app_settings, если её ещё нет, и вставляет дефолты."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '1'
            )
        """)
        # Вставляем дефолты только если ключа ещё нет (INSERT OR IGNORE)
        defaults = [
            ("maintenance_mode",            "0"),
            ("feature_flag_roulette",       "1"),
            ("feature_flag_cases",          "1"),
            ("feature_flag_rocket",         "1"),
            ("feature_flag_limited_gifts",  "1"),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            defaults,
        )
        await db.commit()

# ── Низкоуровневые get / set ──────────────────────────────────────────────────

async def _get(key: str, default: str = "1") -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else default


async def _set(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)"
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()

# ── Maintenance mode ──────────────────────────────────────────────────────────

async def get_maintenance_mode() -> bool:
    return (await _get("maintenance_mode", "0")) == "1"


async def set_maintenance_mode(enabled: bool) -> None:
    await _set("maintenance_mode", "1" if enabled else "0")

# ── Feature flags ─────────────────────────────────────────────────────────────

async def get_feature_flags() -> dict:
    """
    Возвращает словарь флагов видимости разделов.
    Ключи: roulette, cases, rocket, limited_gifts, case_<id>, ...
    Значения: True (видим) / False (скрыт).
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT key, value FROM app_settings WHERE key LIKE 'feature_flag_%'"
        ) as cur:
            rows = await cur.fetchall()

    flags = {}
    for key, value in rows:
        # "feature_flag_roulette" → "roulette"
        flag_name = key.replace("feature_flag_", "", 1)
        flags[flag_name] = value == "1"

    # Гарантируем, что базовые ключи всегда присутствуют
    for name in ("roulette", "cases", "rocket", "limited_gifts"):
        flags.setdefault(name, True)

    return flags


async def set_feature_flag(name: str, enabled: bool) -> None:
    """
    name — например 'roulette', 'cases', 'rocket', 'limited_gifts', 'case_3'.
    """
    await _set(f"feature_flag_{name}", "1" if enabled else "0")
