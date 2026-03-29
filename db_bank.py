# db_bank.py
# Глобальный банк: хранение ликвидности, RTP-статистика, выплаты.
#
# Универсальная единица стоимости (value) = 1 звезда.
# Курс: 1 пончик = config.DONUTS_TO_STARS_RATE звёзд.
# Все пончиковые суммы конвертируются в stars-value перед записью
# в total_deposited_value / total_paid_out_value и при проверках
# платёжеспособности (bank_can_payout, bank_get_max_payout).
# Сами балансы (stars_balance, donuts_balance) хранятся в родных единицах.
# Подарок = его required_value / value из config (в звёздах).

import aiosqlite
from db_core import DB_NAME


async def init_bank():
    """Создаёт таблицу system_bank и безопасно добавляет новые колонки."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_bank (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                -- Ликвидность по типам активов
                stars_balance       INTEGER DEFAULT 0,
                donuts_balance      INTEGER DEFAULT 0,
                gift_value_balance  INTEGER DEFAULT 0,
                -- Суммарная статистика в value-единицах
                total_deposited_value   INTEGER DEFAULT 0,
                total_paid_out_value    INTEGER DEFAULT 0,
                total_house_edge_value  INTEGER DEFAULT 0,
                -- Статистика по типам (для детального RTP)
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
        + bank.get("donuts_balance", 0) * rate
        + bank.get("gift_value_balance", 0)
    )


# ── Универсальный депозит ─────────────────────────────────────────────────────

async def bank_deposit(gross_bet: int, house_edge: float,
                       asset_type: str = "stars") -> dict:
    """
    Вносит ставку в банк для указанного типа актива.

    asset_type: "stars" | "donuts"
    (gift_value не является ставкой и в депозит не передаётся)

    Возвращает house_edge_amount, pool_amount, new_balance (суммарный).
    """
    import time
    house_edge_amount = int(gross_bet * house_edge)
    pool_amount = gross_bet - house_edge_amount

    if asset_type == "donuts":
        balance_col   = "donuts_balance"
        deposited_col = "donuts_deposited"
    elif asset_type == "gift_value":
        # gift_value — обязательство, не депозит; только пополняем резерв
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
            new_balance = (row[0] + row[1] + row[2]) if row else 0

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

    Логика двухуровневая:
      1. Строгая проверка — хватает ли баланса конкретного актива.
      2. Мягкий fallback — хватает ли суммарной ликвидности в stars-value.
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


# ── Универсальная выплата ─────────────────────────────────────────────────────

async def bank_payout(amount: int, asset_type: str = "stars") -> bool:
    """
    Списывает выплату из банка.

    Сначала списывает с основного актива, нехватку добирает из остальных
    жадным алгоритмом (без потери единиц на округлении).
    Возвращает True при успехе, False если ликвидности недостаточно.
    """
    import time

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
        async with db.execute(
            "SELECT stars_balance, donuts_balance, gift_value_balance FROM system_bank WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            stars_bal, donuts_bal, gift_bal = row[0], row[1], row[2]
            total_liquidity = stars_bal + donuts_bal + gift_bal

        if total_liquidity < amount:
            return False

        asset_bal      = {"stars": stars_bal, "donuts": donuts_bal, "gift_value": gift_bal}.get(asset_type, stars_bal)
        primary_deduct = min(amount, asset_bal)
        remainder      = amount - primary_deduct

        if remainder > 0:
            other_assets = [
                ("stars_balance",      "stars_paid_out",      stars_bal),
                ("donuts_balance",     "donuts_paid_out",     donuts_bal),
                ("gift_value_balance", "gift_value_paid_out", gift_bal),
            ]
            other_available = [(col, pc, bal) for col, pc, bal in other_assets
                               if col != balance_col and bal > 0]

            still_needed  = remainder
            extra_updates = []
            for col, pc, bal in other_available:
                if still_needed <= 0:
                    break
                deduct = min(bal, still_needed)
                still_needed -= deduct
                extra_updates.append((col, pc, deduct))

            for col, pc, deduct in extra_updates:
                await db.execute(f"""
                    UPDATE system_bank SET
                        {col} = {col} - ?,
                        {pc}  = {pc} + ?,
                        updated_at = ?
                    WHERE id = 1
                """, (deduct, deduct, int(time.time())))

        import config as _cfg
        rate     = _cfg.DONUTS_TO_STARS_RATE if asset_type == "donuts" else 1
        amount_v = amount * rate
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
    Суммарная ликвидность считается в stars-value, затем конвертируется
    обратно в запрошенный актив по курсу DONUTS_TO_STARS_RATE.
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
    import time
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
    import time
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE system_bank SET
                donuts_balance        = donuts_balance + ?,
                donuts_deposited      = donuts_deposited + ?,
                total_deposited_value = total_deposited_value + ?,
                updated_at            = ?
            WHERE id = 1
        """, (amount, amount, amount, int(time.time())))
        await db.commit()
