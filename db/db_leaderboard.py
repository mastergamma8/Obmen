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
    """Транжиры: топ по суммарным тратам пончиков и звёзд за текущую неделю."""
    week_start = _get_week_start_ts()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"""
            SELECT
                h.user_id AS tg_id,
                u.username,
                u.first_name,
                u.photo_url,
                ABS(SUM(CASE WHEN h.action_type != 'case_paid_stars'
                              AND h.action_type != 'roulette_paid_stars'
                              AND h.action_type != 'rocket_lose_stars'
                         THEN h.amount ELSE 0 END)) AS donuts_spent,
                ABS(SUM(CASE WHEN h.action_type IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                         THEN h.amount ELSE 0 END)) AS stars_spent
            FROM user_history h
            JOIN users u ON u.tg_id = h.user_id
            WHERE h.created_at >= ?
              AND h.amount < 0
              AND h.action_type IN ({_SPEND_TYPES_PLACEHOLDER})
            GROUP BY h.user_id
            ORDER BY (ABS(SUM(h.amount))) DESC
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
    """Возвращает место и суммарные траты пользователя в таблице транжир за текущую неделю."""
    week_start = _get_week_start_ts()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"""
            SELECT ABS(SUM(h.amount)) AS total_spent
            FROM user_history h
            WHERE h.user_id = ?
              AND h.created_at >= ?
              AND h.amount < 0
              AND h.action_type IN ({_SPEND_TYPES_PLACEHOLDER})
        """, (tg_id, week_start, *_SPEND_ACTION_TYPES)) as cursor:
            row = await cursor.fetchone()
            if not row or not row["total_spent"]:
                return {"rank": None, "donuts_spent": 0, "stars_spent": 0}
            total_spent = row["total_spent"]

        async with db.execute(f"""
            SELECT COUNT(*) as cnt FROM (
                SELECT user_id, ABS(SUM(amount)) AS ts
                FROM user_history
                WHERE created_at >= ?
                  AND amount < 0
                  AND action_type IN ({_SPEND_TYPES_PLACEHOLDER})
                GROUP BY user_id
                HAVING ts > ?
            )
        """, (week_start, *_SPEND_ACTION_TYPES, total_spent)) as cursor:
            cnt_row = await cursor.fetchone()
            rank = cnt_row["cnt"] + 1

        # Отдельно считаем пончики и звёзды для отображения
        async with db.execute(f"""
            SELECT
                ABS(SUM(CASE WHEN action_type NOT IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                         THEN amount ELSE 0 END)) AS donuts_spent,
                ABS(SUM(CASE WHEN action_type IN ('case_paid_stars','roulette_paid_stars','rocket_lose_stars')
                         THEN amount ELSE 0 END)) AS stars_spent
            FROM user_history
            WHERE user_id = ?
              AND created_at >= ?
              AND amount < 0
              AND action_type IN ({_SPEND_TYPES_PLACEHOLDER})
        """, (tg_id, week_start, *_SPEND_ACTION_TYPES)) as cursor:
            spend_row = await cursor.fetchone()

    return {
        "rank": rank,
        "donuts_spent": spend_row["donuts_spent"] or 0 if spend_row else 0,
        "stars_spent": spend_row["stars_spent"] or 0 if spend_row else 0,
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
