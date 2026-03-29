import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import config
import database
from routers import users, gifts, games, tasks, bank

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация базы данных
    await database.init_db()
    await database.init_bank()
    
    # --- ДОБАВЛЕННЫЙ КОД ---
    # Обновляем цены подарков из API Portals при запуске веб-приложения
    print("Инициализация обновления цен подарков (API Portals)...")
    config.update_base_gifts_prices()
    # -----------------------
    
    yield

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

# Монтирование статических директорий
os.makedirs("gifts", exist_ok=True)
app.mount("/gifts", StaticFiles(directory="gifts"), name="gifts")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("partials", exist_ok=True)
app.mount("/partials", StaticFiles(directory="partials"), name="partials")

os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

# Подключение модулей
app.include_router(users.router)
app.include_router(gifts.router)
app.include_router(games.router)
app.include_router(tasks.router)
app.include_router(bank.router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)