# db_leaderboard.py
# Таблицы лидеров: богачи, сорвиголовы (ракета), счастливчики (кейсы).

import aiosqlite
from db.db_core import DB_NAME


# ==========================================
# ТАБЛИЦЫ ЛИДЕРОВ
# ==========================================

async def get_leaderboard():
    """Богачи: топ по балансу пончиков."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT tg_id, username, first_name, photo_url, balance AS total_gifts
            FROM users
            ORDER BY balance DESC
            LIMIT 50
        """) as cursor:
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
