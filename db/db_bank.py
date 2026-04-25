# db_bank.py
# Глобальный банк: хранение ликвидности, RTP-статистика, выплаты.
#
# Универсальная единица стоимости (value) = 1 звезда.
# Курс: 1 пончик = config.DONUTS_TO_STARS_RATE звёзд.
# Все пончиковые суммы конвертируются в stars-value при записи
# в total_deposited_value / total_paid_out_value и при проверках
# платёжеспособности (bank_can_payout, bank_get_max_payout).
# Сами балансы (stars_balance, donuts_balance) хранятся в родных единицах.

import math
import time
import aiosqlite
from datetime import datetime, timezone
from db.db_core import DB_NAME


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _today_utc() -> str:
    """Возвращает сегодняшнюю дату в формате YYYY-MM-DD (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _day_start_ts() -> int:
    """Unix-timestamp начала сегодняшнего дня (00:00 UTC)."""
    now = datetime.now(timezone.utc)
    return int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


# ─────────────────────────────────────────────────────────────────────────────
# Инициализация таблиц
# ─────────────────────────────────────────────────────────────────────────────

async def init_bank():
    """Создаёт таблицы system_bank и bank_day_stats, добавляет индексы."""
    async with aiosqlite.connect(DB_NAME) as db:

        # ── Основная таблица банка ────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_bank (
                id                     INTEGER PRIMARY KEY CHECK (id = 1),
                stars_balance          INTEGER DEFAULT 0,
                donuts_balance         INTEGER DEFAULT 0,
                gift_value_balance     INTEGER DEFAULT 0,
                total_deposited_value  INTEGER DEFAULT 0,
                total_paid_out_value   INTEGER DEFAULT 0,
                total_house_edge_value INTEGER DEFAULT 0,
                stars_deposited        INTEGER DEFAULT 0,
                stars_paid_out         INTEGER DEFAULT 0,
                donuts_deposited       INTEGER DEFAULT 0,
                donuts_paid_out        INTEGER DEFAULT 0,
                gift_value_paid_out    INTEGER DEFAULT 0,
                games_count            INTEGER DEFAULT 0,
                updated_at             INTEGER DEFAULT 0
            )
        """)
        await db.execute("INSERT OR IGNORE INTO system_bank (id) VALUES (1)")

        # Безопасная миграция: добавляем только отсутствующие колонки
        _safe_columns = [
            ("donuts_balance",          "INTEGER DEFAULT 0"),
            ("gift_value_balance",      "INTEGER DEFAULT 0"),
            ("total_deposited_value",   "INTEGER DEFAULT 0"),
            ("total_paid_out_value",    "INTEGER DEFAULT 0"),
            ("total_house_edge_value",  "INTEGER DEFAULT 0"),
            ("stars_deposited",         "INTEGER DEFAULT 0"),
            ("stars_paid_out",          "INTEGER DEFAULT 0"),
            ("donuts_deposited",        "INTEGER DEFAULT 0"),
            ("donuts_paid_out",         "INTEGER DEFAULT 0"),
            ("gift_value_paid_out",     "INTEGER DEFAULT 0"),
            ("games_count",             "INTEGER DEFAULT 0"),
        ]
        for col_name, col_def in _safe_columns:
            try:
                await db.execute(f"ALTER TABLE system_bank ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

        # Перенос legacy-колонок при первом запуске после миграции
        try:
            await db.execute("""
                UPDATE system_bank
                SET
                    total_deposited_value  = COALESCE(total_deposited, total_deposited_value),
                    total_paid_out_value   = COALESCE(total_paid_out, total_paid_out_value),
                    total_house_edge_value = COALESCE(total_house_edge, total_house_edge_value),
                    stars_deposited        = COALESCE(total_deposited, stars_deposited),
                    stars_paid_out         = COALESCE(total_paid_out, stars_paid_out)
                WHERE id = 1
                  AND total_deposited_value = 0
                  AND (total_deposited > 0 OR total_house_edge > 0)
            """)
        except Exception:
            pass

        # ── Ежедневная статистика ─────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bank_day_stats (
                day_date         TEXT    PRIMARY KEY,
                deposited_value  INTEGER DEFAULT 0,
                paid_out_value   INTEGER DEFAULT 0,
                house_edge_value INTEGER DEFAULT 0,
                games_count      INTEGER DEFAULT 0,
                stars_deposited  INTEGER DEFAULT 0,
                stars_paid_out   INTEGER DEFAULT 0,
                donuts_deposited INTEGER DEFAULT 0,
                donuts_paid_out  INTEGER DEFAULT 0
            )
        """)

        # ── Индексы для производительности (leaderboard / history) ───────────
        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_uh_user_date ON user_history (user_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_uh_action_date ON user_history (action_type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_uh_amount ON user_history (amount, created_at)",
        ]:
            try:
                await db.execute(ddl)
            except Exception:
                pass

        await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Чтение состояния банка
# ─────────────────────────────────────────────────────────────────────────────

async def get_bank() -> dict:
    """Возвращает текущее состояние банка."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM system_bank WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "stars_balance": 0, "donuts_balance": 0, "gift_value_balance": 0,
                "total_deposited_value": 0, "total_paid_out_value": 0,
                "total_house_edge_value": 0,
                "stars_deposited": 0, "stars_paid_out": 0,
                "donuts_deposited": 0, "donuts_paid_out": 0,
                "gift_value_paid_out": 0, "games_count": 0,
            }


def _bank_liquidity(bank: dict) -> int:
    """Суммарная ликвидность банка в stars-value."""
    import config as _cfg
    rate = _cfg.DONUTS_TO_STARS_RATE
    return (
        bank.get("stars_balance", 0)
        + bank.get("donuts_balance", 0) * rate
        + bank.get("gift_value_balance", 0)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Дневная статистика
# ─────────────────────────────────────────────────────────────────────────────

async def get_bank_day_stats(day: str = None) -> dict:
    """
    Статистика банка за конкретный день.
    day: YYYY-MM-DD (UTC). По умолчанию — сегодня.
    """
    if day is None:
        day = _today_utc()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bank_day_stats WHERE day_date = ?", (day,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "day_date": day, "deposited_value": 0, "paid_out_value": 0,
                "house_edge_value": 0, "games_count": 0,
                "stars_deposited": 0, "stars_paid_out": 0,
                "donuts_deposited": 0, "donuts_paid_out": 0,
            }


async def get_bank_day_history(days: int = 7) -> list:
    """Статистика за последние N дней (по убыванию даты)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM bank_day_stats
            ORDER BY day_date DESC
            LIMIT ?
        """, (days,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Топ активных игроков сегодня
# ─────────────────────────────────────────────────────────────────────────────

_GAME_ACTION_TYPES = (
    "case_paid_donuts", "case_paid_stars",
    "roulette_paid_donuts", "roulette_paid_stars",
    "rocket_lose_donuts", "rocket_lose_stars",
    "rocket_win_donuts", "rocket_win_stars",
)
_GAME_TYPES_PH = ",".join("?" * len(_GAME_ACTION_TYPES))


async def get_top_active_today(limit: int = 3) -> list:
    """
    Топ самых активных игроков за сегодня по количеству игр.
    Поля: tg_id, username, first_name, games_today, volume_today.
    """
    day_start = _day_start_ts()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"""
            SELECT
                h.user_id,
                u.username,
                u.first_name,
                COUNT(*) AS games_today,
                COALESCE(ABS(SUM(CASE WHEN h.amount < 0 THEN h.amount ELSE 0 END)), 0)
                    AS volume_today
            FROM user_history h
            JOIN users u ON u.tg_id = h.user_id
            WHERE h.created_at >= ?
              AND h.action_type IN ({_GAME_TYPES_PH})
            GROUP BY h.user_id
            ORDER BY games_today DESC
            LIMIT ?
        """, (day_start, *_GAME_ACTION_TYPES, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Сводка доходов банка
# ─────────────────────────────────────────────────────────────────────────────

async def get_bank_earnings_summary() -> dict:
    """
    Возвращает сводку доходов:
      gross_deposited — всего принято ставок (stars-value)
      total_paid_out  — всего выплачено игрокам (stars-value)
      house_edge      — заработано казино (комиссия, stars-value)
      games_count     — всего игр сыграно
      rtp_percent     — общий RTP в %
    """
    bank = await get_bank()
    total_dep  = bank.get("total_deposited_value", 0)
    total_paid = bank.get("total_paid_out_value", 0)
    total_edge = bank.get("total_house_edge_value", 0)
    games      = bank.get("games_count", 0)
    rtp = round(total_paid / total_dep * 100, 2) if total_dep > 0 else 0.0
    return {
        "gross_deposited": total_dep,
        "total_paid_out":  total_paid,
        "house_edge":      total_edge,
        "games_count":     games,
        "rtp_percent":     rtp,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Депозит (ставка в банк)
# ─────────────────────────────────────────────────────────────────────────────

async def bank_deposit(gross_bet: int, house_edge: float,
                       asset_type: str = "stars") -> dict:
    """
    Вносит ставку в банк для указанного типа актива.
    asset_type: "stars" | "donuts" | "gift_value"
    Возвращает house_edge_amount, pool_amount, new_balance (stars-value).

    ФИХ: добавлено обновление bank_day_stats и games_count.
    """
    # ФИХ: math.ceil вместо int() — маленькие ставки больше не дают нулевую комиссию.
    # При house_edge > 0 казино всегда получает минимум 1 единицу с любой ставки.
    # Переполнения нет: house_edge < 1.0, поэтому house_edge_amount < gross_bet всегда.
    house_edge_amount = math.ceil(gross_bet * house_edge) if house_edge > 0 else 0
    pool_amount       = gross_bet - house_edge_amount

    if asset_type == "donuts":
        balance_col   = "donuts_balance"
        deposited_col = "donuts_deposited"
    elif asset_type == "gift_value":
        balance_col   = "gift_value_balance"
        deposited_col = None
    else:
        balance_col   = "stars_balance"
        deposited_col = "stars_deposited"

    today = _today_utc()

    async with aiosqlite.connect(DB_NAME) as db:
        if deposited_col is not None:
            import config as _cfg
            rate        = _cfg.DONUTS_TO_STARS_RATE if asset_type == "donuts" else 1
            gross_bet_v = gross_bet         * rate
            edge_v      = house_edge_amount * rate

            await db.execute(f"""
                UPDATE system_bank SET
                    {balance_col}          = {balance_col} + ?,
                    {deposited_col}        = {deposited_col} + ?,
                    total_deposited_value  = total_deposited_value + ?,
                    total_house_edge_value = total_house_edge_value + ?,
                    games_count            = games_count + 1,
                    updated_at             = ?
                WHERE id = 1
            """, (pool_amount, gross_bet, gross_bet_v, edge_v, int(time.time())))

            day_dep_col = "stars_deposited" if asset_type == "stars" else "donuts_deposited"
            await db.execute(f"""
                INSERT INTO bank_day_stats
                    (day_date, deposited_value, house_edge_value, games_count, {day_dep_col})
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(day_date) DO UPDATE SET
                    deposited_value  = deposited_value  + excluded.deposited_value,
                    house_edge_value = house_edge_value + excluded.house_edge_value,
                    games_count      = games_count + 1,
                    {day_dep_col}    = {day_dep_col} + excluded.{day_dep_col}
            """, (today, gross_bet_v, edge_v, gross_bet))

        else:
            # ФИХ gift_value: конвертируем в stars-value и пишем в полную статистику,
            # как для звёзд и пончиков. Стоимость одного gift_value = 1 звезда
            # (gift_value_balance уже хранится в эквивалентных единицах).
            import config as _cfg
            gross_bet_v = gross_bet         # gift_value unit == 1 star by convention
            edge_v      = house_edge_amount # то же

            await db.execute(f"""
                UPDATE system_bank SET
                    {balance_col}          = {balance_col} + ?,
                    gift_value_paid_out    = gift_value_paid_out + 0,
                    total_deposited_value  = total_deposited_value + ?,
                    total_house_edge_value = total_house_edge_value + ?,
                    games_count            = games_count + 1,
                    updated_at             = ?
                WHERE id = 1
            """, (pool_amount, gross_bet_v, edge_v, int(time.time())))

            await db.execute("""
                INSERT INTO bank_day_stats
                    (day_date, deposited_value, house_edge_value, games_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(day_date) DO UPDATE SET
                    deposited_value  = deposited_value  + excluded.deposited_value,
                    house_edge_value = house_edge_value + excluded.house_edge_value,
                    games_count      = games_count + 1
            """, (today, gross_bet_v, edge_v))

        async with db.execute(
            "SELECT stars_balance, donuts_balance, gift_value_balance FROM system_bank WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            import config as _cfg
            rate = _cfg.DONUTS_TO_STARS_RATE
            new_balance = (row[0] + row[1] * rate + row[2]) if row else 0

        await db.commit()

    return {
        "house_edge_amount": house_edge_amount,
        "pool_amount":       pool_amount,
        "new_balance":       new_balance,
        "asset_type":        asset_type,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Проверка платёжеспособности
# ─────────────────────────────────────────────────────────────────────────────

async def bank_can_payout(amount: int, asset_type: str = "stars") -> bool:
    """Проверяет, может ли банк выплатить заданную сумму."""
    import config as _cfg
    bank = await get_bank()
    asset_bal = {
        "stars":      bank.get("stars_balance", 0),
        "donuts":     bank.get("donuts_balance", 0),
        "gift_value": bank.get("gift_value_balance", 0),
    }.get(asset_type, 0)

    if asset_bal >= amount:
        return True
    rate = _cfg.DONUTS_TO_STARS_RATE if asset_type == "donuts" else 1
    return _bank_liquidity(bank) >= amount * rate


# ─────────────────────────────────────────────────────────────────────────────
# Выплата (атомарная, защищена BEGIN IMMEDIATE)
# ─────────────────────────────────────────────────────────────────────────────

async def bank_payout(amount: int, asset_type: str = "stars") -> bool:
    """
    Атомарно списывает выплату из банка.
    Сначала списывает с основного актива; нехватку добирает из остальных.
    Возвращает True при успехе, False если ликвидности недостаточно.

    ФИХ: использован math.ceil для корректного округления кросс-актив вычетов;
         добавлено обновление bank_day_stats.
    """
    if asset_type == "donuts":
        balance_col  = "donuts_balance"
        paid_out_col = "donuts_paid_out"
    elif asset_type == "gift_value":
        balance_col  = "gift_value_balance"
        paid_out_col = "gift_value_paid_out"
    else:
        balance_col  = "stars_balance"
        paid_out_col = "stars_paid_out"

    today = _today_utc()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")

        async with db.execute(
            "SELECT stars_balance, donuts_balance, gift_value_balance FROM system_bank WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return False
            stars_bal, donuts_bal, gift_bal = row[0], row[1], row[2]

        import config as _cfg
        rate = _cfg.DONUTS_TO_STARS_RATE
        total_liquidity = stars_bal + donuts_bal * rate + gift_bal

        # Переводим требуемую сумму в stars-value, чтобы сравнивать с total_liquidity
        # корректно для любого asset_type. Без этого пончиковая выплата сравнивалась
        # бы с суммарной ликвидностью в звёздах без конвертации — критическая ошибка.
        required_liquidity = amount * (rate if asset_type == "donuts" else 1)
        if total_liquidity < required_liquidity:
            await db.rollback()
            return False

        asset_bal      = {"stars": stars_bal, "donuts": donuts_bal, "gift_value": gift_bal}.get(asset_type, stars_bal)
        primary_deduct = min(amount, asset_bal)
        remainder      = amount - primary_deduct

        extra_updates = []
        if remainder > 0:
            remainder_in_stars = remainder * (rate if asset_type == "donuts" else 1)
            other_assets = [
                ("stars_balance",      "stars_paid_out",      stars_bal,  1),
                ("donuts_balance",     "donuts_paid_out",     donuts_bal, rate),
                ("gift_value_balance", "gift_value_paid_out", gift_bal,   1),
            ]
            other_available = [
                (col, pc, bal, col_rate)
                for col, pc, bal, col_rate in other_assets
                if col != balance_col and bal > 0
            ]
            still_needed = remainder_in_stars
            for col, pc, bal, col_rate in other_available:
                if still_needed <= 0:
                    break
                raw_needed = still_needed / col_rate if col_rate > 0 else still_needed
                # math.ceil гарантирует покрытие нехватки без ручной арифметики
                deduct = min(bal, math.ceil(raw_needed))
                still_needed -= deduct * col_rate
                extra_updates.append((col, pc, deduct))

            # Проверяем, что ликвидности хватило на полное покрытие.
            # Если still_needed > 0 — между первичной проверкой и сюда что-то
            # изменилось (race condition при слабой изоляции) или логика сломана.
            # Откатываем транзакцию, чтобы не выдать меньше, чем должны.
            if still_needed > 0:
                await db.rollback()
                return False

            for col, pc, deduct in extra_updates:
                await db.execute(f"""
                    UPDATE system_bank SET
                        {col} = {col} - ?,
                        {pc}  = {pc} + ?,
                        updated_at = ?
                    WHERE id = 1
                """, (deduct, deduct, int(time.time())))

        payout_rate = _cfg.DONUTS_TO_STARS_RATE if asset_type == "donuts" else 1
        amount_v    = amount * payout_rate

        await db.execute(f"""
            UPDATE system_bank SET
                {balance_col}        = {balance_col} - ?,
                {paid_out_col}       = {paid_out_col} + ?,
                total_paid_out_value = total_paid_out_value + ?,
                updated_at           = ?
            WHERE id = 1
        """, (primary_deduct, primary_deduct, amount_v, int(time.time())))

        # Обновляем дневные выплаты
        day_paid_col = (
            "stars_paid_out"  if asset_type == "stars"  else
            "donuts_paid_out" if asset_type == "donuts" else None
        )
        if day_paid_col:
            await db.execute(f"""
                INSERT INTO bank_day_stats (day_date, paid_out_value, {day_paid_col})
                VALUES (?, ?, ?)
                ON CONFLICT(day_date) DO UPDATE SET
                    paid_out_value = paid_out_value + excluded.paid_out_value,
                    {day_paid_col} = {day_paid_col} + excluded.{day_paid_col}
            """, (today, amount_v, primary_deduct))

        await db.commit()

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Максимальная выплата
# ─────────────────────────────────────────────────────────────────────────────

async def bank_get_max_payout(asset_type: str = "stars") -> int:
    """Возвращает максимально допустимую выплату в единицах asset_type."""
    import config as _cfg
    bank      = await get_bank()
    liq_stars = _bank_liquidity(bank)
    if asset_type == "donuts":
        rate = _cfg.DONUTS_TO_STARS_RATE
        return liq_stars // rate if rate > 0 else 0
    return liq_stars


# ─────────────────────────────────────────────────────────────────────────────
# Ручное пополнение банка (администратор)
# ─────────────────────────────────────────────────────────────────────────────

async def bank_add_stars(amount: int):
    """Пополнение банка звёздами (администратором). Не учитывается как игровой доход."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE system_bank SET
                stars_balance         = stars_balance + ?,
                stars_deposited       = stars_deposited + ?,
                total_deposited_value = total_deposited_value + ?,
                updated_at            = ?
            WHERE id = 1
        """, (amount, amount, amount, int(time.time())))
        await db.commit()


async def bank_add_donuts(amount: int):
    """Пополнение банка пончиками (администратором). Конвертируется в stars-value."""
    import config as _cfg
    rate  = _cfg.DONUTS_TO_STARS_RATE
    value = amount * rate
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE system_bank SET
                donuts_balance        = donuts_balance + ?,
                donuts_deposited      = donuts_deposited + ?,
                total_deposited_value = total_deposited_value + ?,
                updated_at            = ?
            WHERE id = 1
        """, (amount, amount, value, int(time.time())))
        await db.commit()
