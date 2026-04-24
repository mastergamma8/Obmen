# db_leaderboard.py
# Таблицы лидеров: транжиры (трата за неделю), сорвиголовы (ракета), счастливчики (кейсы).

import time
from datetime import datetime, timezone, timedelta

import aiosqlite
from db.db_core import DB_NAME


def _get_week_start_ts() -> int:
    """Возвращает Unix-timestamp начала текущей недели (понедельник 00:00 UTC)."""
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(monday.timestamp())


def get_week_reset_ts() -> int:
    """Возвращает Unix-timestamp ближайшего сброса лидерборда (следующий понедельник 00:00 UTC)."""
    return _get_week_start_ts() + 7 * 86400


# Типы действий, которые считаются «расходом» пончиков или звёзд
_SPEND_ACTION_TYPES = (
    'case_paid_donuts', 'case_paid_stars',
    'roulette_paid_donuts', 'roulette_paid_stars',
    'rocket_lose_donuts', 'rocket_lose_stars',
    'claim_gift',
)

_SPEND_TYPES_PLACEHOLDER = ','.join('?' * len(_SPEND_ACTION_TYPES))


# ==========================================
# ТАБЛИЦЫ ЛИДЕРОВ
# ==========================================

async def get_leaderboard():
    """Транжиры: топ по суммарным тратам за текущую неделю.
    Включает всех пользователей, даже с нулевыми тратами."""
    week_start = _get_week_start_ts()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"""
            SELECT
                u.tg_id,
                u.username,
                u.first_name,
                u.photo_url,
                COALESCE(ABS(SUM(CASE
                    WHEN h.action_type NOT IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                    THEN h.amount ELSE 0 END)), 0) AS donuts_spent,
                COALESCE(ABS(SUM(CASE
                    WHEN h.action_type IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                    THEN h.amount ELSE 0 END)), 0) AS stars_spent
            FROM users u
            LEFT JOIN user_history h
                ON  h.user_id     = u.tg_id
                AND h.created_at  >= ?
                AND h.amount      < 0
                AND h.action_type IN ({_SPEND_TYPES_PLACEHOLDER})
            GROUP BY u.tg_id
            ORDER BY COALESCE(ABS(SUM(h.amount)), 0) DESC
            LIMIT 50
        """, (week_start, *_SPEND_ACTION_TYPES)) as cursor:
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

async def get_user_rich_rank(tg_id: int) -> dict:
    """Возвращает место и суммарные траты пользователя в таблице транжир за текущую неделю.
    Корректно работает для пользователей с нулевыми тратами."""
    week_start = _get_week_start_ts()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        # Траты самого пользователя
        async with db.execute(f"""
            SELECT COALESCE(ABS(SUM(amount)), 0) AS total_spent
            FROM user_history
            WHERE user_id = ? AND created_at >= ? AND amount < 0
              AND action_type IN ({_SPEND_TYPES_PLACEHOLDER})
        """, (tg_id, week_start, *_SPEND_ACTION_TYPES)) as cursor:
            row = await cursor.fetchone()
            total_spent = row["total_spent"] if row else 0

        # Количество пользователей, которые потратили БОЛЬШЕ
        async with db.execute(f"""
            SELECT COUNT(*) AS cnt FROM (
                SELECT u.tg_id,
                       COALESCE(ABS(SUM(h.amount)), 0) AS ts
                FROM users u
                LEFT JOIN user_history h
                    ON  h.user_id     = u.tg_id
                    AND h.created_at  >= ?
                    AND h.amount      < 0
                    AND h.action_type IN ({_SPEND_TYPES_PLACEHOLDER})
                WHERE u.tg_id != ?
                GROUP BY u.tg_id
                HAVING ts > ?
            )
        """, (week_start, *_SPEND_ACTION_TYPES, tg_id, total_spent)) as cursor:
            cnt_row = await cursor.fetchone()
            rank = (cnt_row["cnt"] + 1) if cnt_row else 1

        # Разбивка по пончикам и звёздам
        async with db.execute(f"""
            SELECT
                COALESCE(ABS(SUM(CASE WHEN action_type NOT IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                             THEN amount ELSE 0 END)), 0) AS donuts_spent,
                COALESCE(ABS(SUM(CASE WHEN action_type IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                             THEN amount ELSE 0 END)), 0) AS stars_spent
            FROM user_history
            WHERE user_id = ? AND created_at >= ? AND amount < 0
              AND action_type IN ({_SPEND_TYPES_PLACEHOLDER})
        """, (tg_id, week_start, *_SPEND_ACTION_TYPES)) as cursor:
            spend_row = await cursor.fetchone()

    return {
        "rank": rank,
        "donuts_spent": spend_row["donuts_spent"] if spend_row else 0,
        "stars_spent":  spend_row["stars_spent"]  if spend_row else 0,
    }


async def get_rocket_leaderboard_full():
    """Возвращает полную таблицу сорвиголов (без ограничения 50) для расчёта ранга."""
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
    return sorted(best.values(), key=lambda x: x["max_multiplier"], reverse=True)


async def get_user_lucky_rank(tg_id: int) -> dict:
    """Возвращает реальное место и лучший коэффициент пользователя в таблице счастливчиков."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT MAX(amount) as best FROM user_history
            WHERE user_id = ? AND action_type = 'case_lucky_ratio'
        """, (tg_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row["best"] is None:
                return {"rank": None, "ratio": None}
            user_best = row["best"]
        async with db.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT user_id FROM user_history
                WHERE action_type = 'case_lucky_ratio'
                GROUP BY user_id
                HAVING MAX(amount) > ?
            )
        """, (user_best,)) as cursor:
            cnt_row = await cursor.fetchone()
            rank = cnt_row["cnt"] + 1
    return {"rank": rank, "ratio": user_best / 100}


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
