# database.py
import aiosqlite

DB_NAME = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                photo_url TEXT
            )
        """)
        # Таблица инвентаря подарков пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_gifts (
                user_id INTEGER,
                gift_id INTEGER,
                amount INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, gift_id)
            )
        """)
        await db.commit()

async def upsert_user(tg_id: int, username: str, first_name: str, photo_url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (tg_id, username, first_name, photo_url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                photo_url=excluded.photo_url
        """, (tg_id, username, first_name, photo_url))
        await db.commit()

async def add_gift_to_user(user_id: int, gift_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_gifts (user_id, gift_id, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, gift_id) DO UPDATE SET
                amount = amount + excluded.amount
        """, (user_id, gift_id, amount))
        await db.commit()

async def get_user_gifts(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT gift_id, amount FROM user_gifts WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row["gift_id"]: row["amount"] for row in rows}

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Считаем общее количество подарков у каждого пользователя
        query = """
            SELECT u.tg_id, u.username, u.first_name, u.photo_url, IFNULL(SUM(ug.amount), 0) as total_gifts
            FROM users u
            LEFT JOIN user_gifts ug ON u.tg_id = ug.user_id
            GROUP BY u.tg_id
            ORDER BY total_gifts DESC
            LIMIT 50
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
