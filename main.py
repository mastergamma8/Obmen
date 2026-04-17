import os
import time
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import aiosqlite
import config
import database
from routers import users, gifts, games, tasks, bank
from routers import games_roulette, games_rocket, games_cases
from routers import tg_shop
from db.db_core import DB_NAME


# ── Rate Limiter (SQLite-backed, multi-process safe) ──────────────────────────
#
# Хранит временны́е метки запросов в таблице rate_limit_log.
# В отличие от in-memory dict, работает корректно при нескольких
# воркерах uvicorn или нескольких инстансах приложения.
#
# Схема: (ip TEXT, path_prefix TEXT, ts INTEGER)
# Индекс по (ip, path_prefix, ts) делает очистку устаревших записей быстрой.

# (путь_prefix, max_requests, window_seconds)
RATE_LIMITS: list[tuple[str, int, int]] = [
    ("/api/init",           30, 60),
    ("/api/topup/stars",    10, 60),
    ("/roulette/spin",      20, 60),
    ("/rocket/start",       20, 60),
    ("/rocket/cashout",     20, 60),
    ("/api/gifts/claim",    10, 60),
    ("/api/gifts/withdraw",  5, 60),
    ("/api/withdraw",        5, 60),
    ("/api/claim",          10, 60),
    ("/api/tg_shop/buy",     5, 60),
]


async def _init_rate_limit_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_log (
                ip          TEXT    NOT NULL,
                path_prefix TEXT    NOT NULL,
                ts          INTEGER NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rate_limit
            ON rate_limit_log (ip, path_prefix, ts)
        """)
        await db.commit()


async def _check_rate_limit_db(ip: str, path: str) -> bool:
    """
    Скользящее окно через SQLite.
    Возвращает True если запрос разрешён, False если лимит превышен.
    Атомарность обеспечивается через BEGIN IMMEDIATE на запись.
    """
    now = int(time.time())
    for prefix, max_req, window in RATE_LIMITS:
        if not path.startswith(prefix):
            continue

        cutoff = now - window
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")

            # Считаем актуальные запросы в окне
            async with db.execute(
                "SELECT COUNT(*) FROM rate_limit_log WHERE ip = ? AND path_prefix = ? AND ts > ?",
                (ip, prefix, cutoff),
            ) as cur:
                row = await cur.fetchone()
            count = row[0] if row else 0

            if count >= max_req:
                await db.rollback()
                return False

            # Записываем текущий запрос
            await db.execute(
                "INSERT INTO rate_limit_log (ip, path_prefix, ts) VALUES (?, ?, ?)",
                (ip, prefix, now),
            )
            # Чистим устаревшие записи этого ключа (не блокирует других)
            await db.execute(
                "DELETE FROM rate_limit_log WHERE ip = ? AND path_prefix = ? AND ts <= ?",
                (ip, prefix, cutoff),
            )
            await db.commit()
        return True

    return True


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    await database.init_bank()
    await database.init_rocket_games_table()
    await database.init_settings_table()
    await _init_rate_limit_table()

    print("Инициализация обновления цен подарков (API Portals)...")
    config.update_base_gifts_prices()

    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)

origins = [
    config.WEBAPP_URL.rstrip("/"),
    "http://localhost",
    "http://127.0.0.1:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip   = request.client.host if request.client else "unknown"
    path = request.url.path
    if not await _check_rate_limit_db(ip, path):
        return JSONResponse(
            status_code=429,
            content={"detail": "Слишком много запросов. Подождите немного."},
        )
    return await call_next(request)


# ── Maintenance Mode Middleware ───────────────────────────────────────────────

# Эти пути разрешены даже в режиме тех. обслуживания
_MAINTENANCE_WHITELIST = {"/", "/api/features"}

@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    path = request.url.path
    # Разрешаем статические файлы, шаблоны и белый список API
    if (
        path.startswith("/static")
        or path.startswith("/gifts")
        or path.startswith("/partials")
        or path in _MAINTENANCE_WHITELIST
    ):
        return await call_next(request)

    if await database.get_maintenance_mode():
        return JSONResponse(
            status_code=503,
            content={"detail": "maintenance", "message": "Технический перерыв. Следите за обновлениями в @Space_Donut"},
        )
    return await call_next(request)


# ── Static & templates ────────────────────────────────────────────────────────

os.makedirs("gifts",     exist_ok=True)
os.makedirs("static",    exist_ok=True)
os.makedirs("partials",  exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/gifts",    StaticFiles(directory="gifts"),    name="gifts")
app.mount("/static",   StaticFiles(directory="static"),   name="static")
app.mount("/partials", StaticFiles(directory="partials"), name="partials")

templates = Jinja2Templates(directory="templates")


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(users.router)
app.include_router(gifts.router)
app.include_router(games.router)
app.include_router(tasks.router)
app.include_router(bank.router)
app.include_router(games_roulette.router)
app.include_router(games_rocket.router)
app.include_router(games_cases.router)
app.include_router(tg_shop.router)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # reload=False для продакшена — иначе воркеры не шарят состояние и памяти
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
