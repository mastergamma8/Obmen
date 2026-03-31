# db_bank.py
# Глобальный банк: хранение ликвидности, RTP-статистика, выплаты.
#
# Универсальная единица стоимости (value) = 1 звезда.
# Курс: 1 пончик = config.DONUTS_TO_STARS_RATE звёзд.
# Все пончиковые суммы конвертируются в stars-value при записи
# в total_deposited_value / total_paid_out_value и при проверках
# платёжеспособности (bank_can_payout, bank_get_max_payout).
# Сами балансы (stars_balance, donuts_balance) хранятся в родных единицах.

import time
import aiosqlite
from db.db_core import DB_NAME


async def init_bank():
    """Создаёт таблицу system_bank и безопасно добавляет новые колонки."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_bank (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                stars_balance       INTEGER DEFAULT 0,
                donuts_balance      INTEGER DEFAULT 0,
                gift_value_balance  INTEGER DEFAULT 0,
                total_deposited_value   INTEGER DEFAULT 0,
                total_paid_out_value    INTEGER DEFAULT 0,
                total_house_edge_value  INTEGER DEFAULT 0,
                stars_deposited     INTEGER DEFAULT 0,
                stars_paid_out      INTEGER DEFAULT 0,
                donuts_deposited    INTEGER DEFAULT 0,
                donuts_paid_out     INTEGER DEFAULT 0,
                gift_value_paid_out INTEGER DEFAULT 0,
                updated_at          INTEGER DEFAULT 0
            )
        """)
        await db.execute("INSERT OR IGNORE INTO system_bank (id) VALUES (1)")

        new_columns = [
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
        ]
        for col_name, col_def in new_columns:
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

        await db.commit()


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
                "gift_value_paid_out": 0,
            }


def _bank_liquidity(bank: dict) -> int:
    """
    Суммарная ликвидность банка в stars-value.
    Пончики конвертируются по курсу DONUTS_TO_STARS_RATE.
    """
    import config as _cfg
    rate = _cfg.DONUTS_TO_STARS_RATE
    return (
        bank.get("stars_balance", 0)
        + bank.get("donuts_balance", 0) * rate   # FIX: конвертация пончиков
        + bank.get("gift_value_balance", 0)
    )


# ── Универсальный депозит ─────────────────────────────────────────────────────

async def bank_deposit(gross_bet: int, house_edge: float,
                       asset_type: str = "stars") -> dict:
    """
    Вносит ставку в банк для указанного типа актива.
    asset_type: "stars" | "donuts"
    Возвращает house_edge_amount, pool_amount, new_balance (суммарный).
    """
    house_edge_amount = int(gross_bet * house_edge)
    pool_amount = gross_bet - house_edge_amount

    if asset_type == "donuts":
        balance_col   = "donuts_balance"
        deposited_col = "donuts_deposited"
    elif asset_type == "gift_value":
        balance_col   = "gift_value_balance"
        deposited_col = None
    else:  # stars
        balance_col   = "stars_balance"
        deposited_col = "stars_deposited"

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
                    updated_at             = ?
                WHERE id = 1
            """, (pool_amount, gross_bet, gross_bet_v, edge_v, int(time.time())))
        else:
            await db.execute(f"""
                UPDATE system_bank SET
                    {balance_col} = {balance_col} + ?,
                    updated_at    = ?
                WHERE id = 1
            """, (pool_amount, int(time.time())))
        await db.commit()

        async with db.execute(
            "SELECT stars_balance, donuts_balance, gift_value_balance FROM system_bank WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            import config as _cfg
            rate = _cfg.DONUTS_TO_STARS_RATE
            new_balance = (
                row[0] + row[1] * rate + row[2]
            ) if row else 0

    return {
        "house_edge_amount": house_edge_amount,
        "pool_amount": pool_amount,
        "new_balance": new_balance,
        "asset_type": asset_type,
    }


# ── Проверка доступности выплаты ──────────────────────────────────────────────

async def bank_can_payout(amount: int, asset_type: str = "stars") -> bool:
    """
    Проверяет платёжеспособность банка для заданной суммы и типа актива.
    """
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


# ── Универсальная выплата (атомарная) ────────────────────────────────────────

async def bank_payout(amount: int, asset_type: str = "stars") -> bool:
    """
    Атомарно списывает выплату из банка.
    Использует BEGIN IMMEDIATE для защиты от гонок параллельных запросов.

    Сначала списывает с основного актива, нехватку добирает из остальных.
    Возвращает True при успехе, False если ликвидности недостаточно.
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

    async with aiosqlite.connect(DB_NAME) as db:
        # BEGIN IMMEDIATE: немедленный write-lock, защита от race condition
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
        # FIX: ликвидность считается с курсом пончиков
        total_liquidity = stars_bal + donuts_bal * rate + gift_bal

        if total_liquidity < amount:
            await db.rollback()
            return False

        asset_bal      = {"stars": stars_bal, "donuts": donuts_bal, "gift_value": gift_bal}.get(asset_type, stars_bal)
        primary_deduct = min(amount, asset_bal)
        remainder      = amount - primary_deduct

        if remainder > 0:
            # remainder — это нехватка в единицах asset_type.
            # Переводим в stars-value, чтобы правильно списывать из других балансов.
            remainder_in_stars = remainder * (rate if asset_type == "donuts" else 1)

            other_assets = [
                # (balance_col, paid_out_col, raw_balance, col_rate)
                ("stars_balance",      "stars_paid_out",      stars_bal, 1),
                ("donuts_balance",     "donuts_paid_out",     donuts_bal, rate),
                ("gift_value_balance", "gift_value_paid_out", gift_bal,  1),
            ]
            other_available = [
                (col, pc, bal, col_rate)
                for col, pc, bal, col_rate in other_assets
                if col != balance_col and bal > 0
            ]

            still_needed_stars = remainder_in_stars
            extra_updates = []
            for col, pc, bal, col_rate in other_available:
                if still_needed_stars <= 0:
                    break
                # Сколько raw-единиц этого актива покрывают ещё нужные stars-value
                raw_needed = still_needed_stars / col_rate if col_rate > 0 else still_needed_stars
                deduct = min(bal, int(raw_needed) + (1 if raw_needed % 1 > 0 else 0))
                # Не списывать больше, чем реально нужно (округление вверх уже учтено)
                deduct = min(deduct, bal)
                still_needed_stars -= deduct * col_rate
                extra_updates.append((col, pc, deduct))

            for col, pc, deduct in extra_updates:
                await db.execute(f"""
                    UPDATE system_bank SET
                        {col} = {col} - ?,
                        {pc}  = {pc} + ?,
                        updated_at = ?
                    WHERE id = 1
                """, (deduct, deduct, int(time.time())))

        payout_rate = _cfg.DONUTS_TO_STARS_RATE if asset_type == "donuts" else 1
        amount_v = amount * payout_rate
        await db.execute(f"""
            UPDATE system_bank SET
                {balance_col}        = {balance_col} - ?,
                {paid_out_col}       = {paid_out_col} + ?,
                total_paid_out_value = total_paid_out_value + ?,
                updated_at           = ?
            WHERE id = 1
        """, (primary_deduct, primary_deduct, amount_v, int(time.time())))

        await db.commit()

    return True


async def bank_get_max_payout(asset_type: str = "stars") -> int:
    """
    Возвращает максимально допустимую выплату в единицах asset_type.
    """
    import config as _cfg
    bank      = await get_bank()
    liq_stars = _bank_liquidity(bank)
    if asset_type == "donuts":
        rate = _cfg.DONUTS_TO_STARS_RATE
        return liq_stars // rate if rate > 0 else 0
    return liq_stars


# ── Ручное пополнение ─────────────────────────────────────────────────────────

async def bank_add_stars(amount: int):
    """Пополнение банка звёздами вручную (администратором)."""
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
    """Пополнение банка пончиками вручную (администратором)."""
    import config as _cfg
    rate = _cfg.DONUTS_TO_STARS_RATE
    # FIX: конвертируем пончики в value-эквивалент перед записью в total_deposited_value
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
