# main.py
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import httpx 
import time
import random
import hmac
import hashlib
from urllib.parse import parse_qsl

import config
import database

# --- БЛОК БЕЗОПАСНОСТИ ---
def validate_telegram_data(init_data: str) -> bool:
    """Проверяет подлинность данных, пришедших из Telegram Web App."""
    if not init_data:
        return False
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return False
        
        hash_ = parsed_data.pop("hash")
        # Сортируем ключи по алфавиту
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Создаем секретный ключ на основе BOT_TOKEN
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return calculated_hash == hash_
    except Exception:
        return False

# Зависимость (Dependency) для проверки авторизации в API
async def verify_user(x_tg_data: str = Header(None)):
    if not config.BOT_TOKEN:
         raise HTTPException(status_code=500, detail="Токен бота не настроен")
         
    if not x_tg_data or not validate_telegram_data(x_tg_data):
        raise HTTPException(status_code=403, detail="Недействительные данные авторизации Telegram")
    return True
# ------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    yield

app = FastAPI(lifespan=lifespan)

# --- Настройка CORS ---
# Разрешаем запросы только с твоего домена (и для локального тестирования)
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
# ----------------------

os.makedirs("gifts", exist_ok=True)
app.mount("/gifts", StaticFiles(directory="gifts"), name="gifts")
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

# Модели данных (tg_id все еще передаем, но теперь мы доверяем ему благодаря заголовку x_tg_data)
class UserInitData(BaseModel):
    tg_id: int
    username: str = ""
    first_name: str = ""
    photo_url: str = ""

class ActionData(BaseModel):
    tg_id: int
    gift_id: int

class TaskCheckData(BaseModel):
    tg_id: int
    task_id: int

class SpinData(BaseModel):
    tg_id: int


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Добавляем Depends(verify_user) ко всем защищенным роутам!
@app.post("/api/init")
async def init_user(user: UserInitData, is_valid: bool = Depends(verify_user)):
    await database.upsert_user(user.tg_id, user.username, user.first_name, user.photo_url)
    user_data = await database.get_user_data(user.tg_id)
    user_gifts = await database.get_user_gifts(user.tg_id)
    
    return {
        "status": "ok", 
        "balance": user_data.get("balance", 0),
        "user_gifts": user_gifts,
        "config": {
            "base_gifts": config.BASE_GIFTS,
            "main_gifts": config.MAIN_GIFTS,
            "bot_username": config.BOT_USERNAME,
            "roulette": config.ROULETTE_CONFIG
        }
    }

@app.post("/api/claim")
async def claim_gift(data: ActionData, is_valid: bool = Depends(verify_user)):
    if data.gift_id not in config.MAIN_GIFTS:
        raise HTTPException(status_code=400, detail="Неверный ID подарка")
        
    cost = config.MAIN_GIFTS[data.gift_id]["required_value"]
    success = await database.claim_main_gift(data.tg_id, data.gift_id, cost)
    
    if not success:
        raise HTTPException(status_code=400, detail="Недостаточно пончиков")
        
    user_data = await database.get_user_data(data.tg_id)
    user_gifts = await database.get_user_gifts(data.tg_id)
    return {"status": "ok", "balance": user_data["balance"], "user_gifts": user_gifts}

@app.post("/api/withdraw")
async def withdraw_gift(data: ActionData, is_valid: bool = Depends(verify_user)):
    user_gifts = await database.get_user_gifts(data.tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")
        
    await database.remove_gift_from_user(data.tg_id, data.gift_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)
    
    try:
        user_profile = await database.get_user_profile(data.tg_id)
        username_str = f"@{user_profile['username']}" if user_profile.get("username") else "Отсутствует/Скрыт"
        first_name = user_profile.get("first_name", "Без имени")
        
        gift_name = "Неизвестный подарок"
        if data.gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[data.gift_id]["name"]
        elif data.gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[data.gift_id]["name"]
            
        admin_text = (
            f"🚨 <b>Новая заявка на вывод подарка!</b>\n\n"
            f"👤 Пользователь: <a href='tg://user?id={data.tg_id}'>{first_name}</a>\n"
            f"🔗 Юзернейм: {username_str}\n"
            f"🆔 ID: <code>{data.tg_id}</code>\n\n"
            f"🎁 <b>Подарок:</b> {gift_name} (ID: {data.gift_id})"
        )
        
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.ADMIN_ID,
            "text": admin_text,
            "parse_mode": "HTML"
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
            
    except Exception as e:
        print(f"Ошибка при отправке уведомления админу: {e}")
    
    return {"status": "ok", "user_gifts": updated_gifts}

@app.get("/api/leaderboard")
async def get_leaderboard(is_valid: bool = Depends(verify_user)):
    board = await database.get_leaderboard()
    return {"leaderboard": board}

@app.get("/api/roulette/info")
async def get_roulette_info(tg_id: int, is_valid: bool = Depends(verify_user)):
    user_data = await database.get_user_data(tg_id)
    last_spin = user_data.get("last_free_spin", 0)
    now = int(time.time())
    can_free = (now - last_spin) >= 86400 
    
    return {
        "status": "ok",
        "can_free": can_free,
        "cost": config.ROULETTE_CONFIG["cost"],
        "items": config.ROULETTE_CONFIG["items"],
        "time_left": 86400 - (now - last_spin) if not can_free else 0
    }

@app.post("/api/roulette/spin")
async def spin_roulette(data: SpinData, is_valid: bool = Depends(verify_user)):
    user_data = await database.get_user_data(data.tg_id)
    last_spin = user_data.get("last_free_spin", 0)
    now = int(time.time())
    can_free = (now - last_spin) >= 86400

    if can_free:
        await database.update_last_free_spin(data.tg_id, now)
    else:
        cost = config.ROULETTE_CONFIG["cost"]
        if user_data["balance"] < cost:
            raise HTTPException(status_code=400, detail="Недостаточно пончиков для прокрутки")
        await database.add_points_to_user(data.tg_id, -cost)

    items = config.ROULETTE_CONFIG["items"]
    
    # НОВОЕ: Если рулетка бесплатная, гарантированно выдаем 3 пончика
    if can_free:
        win_index = 0
        for i, item in enumerate(items):
            if item.get("type") == "donuts" and item.get("amount") == 1:
                win_index = i
                break
        win_item = items[win_index]
    else:
        # Для платной рулетки используем старую логику рандома
        total_chance = sum(item.get("chance", 0) for item in items)
        if total_chance <= 0:
            total_chance = 100 
            
        r = random.uniform(0, total_chance)
        cumulative = 0
        win_index = 0 
        
        for i, item in enumerate(items):
            chance = item.get("chance", 0)
            if chance <= 0:
                continue 
                
            cumulative += chance
            if r <= cumulative:
                win_index = i
                break
                
        win_item = items[win_index]
    
    if win_item["type"] == "donuts":
        await database.add_points_to_user(data.tg_id, win_item["amount"])
    elif win_item["type"] == "gift":
        await database.add_gift_to_user(data.tg_id, win_item["gift_id"], 1)

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)
    
    return {
        "status": "ok",
        "win_index": win_index,
        "win_item": win_item,
        "balance": updated_user["balance"],
        "user_gifts": updated_gifts,
        "can_free_now": False 
    }

@app.get("/api/earn_data")
async def get_earn_data(tg_id: int, is_valid: bool = Depends(verify_user)):
    referrals = await database.get_referrals(tg_id)
    completed_tasks = await database.get_completed_tasks(tg_id)
    
    tasks_list = []
    for t_id, t_data in config.TASKS.items():
        tasks_list.append({
            "id": t_id,
            "title": t_data["title"],
            "url": t_data["url"],
            "reward": t_data["reward"],
            "completed": t_id in completed_tasks
        })
        
    return {
        "referrals": referrals,
        "tasks": tasks_list
    }

@app.post("/api/check_task")
async def check_task(data: TaskCheckData, is_valid: bool = Depends(verify_user)):
    if data.task_id not in config.TASKS:
        raise HTTPException(status_code=400, detail="Задание не найдено")
        
    completed = await database.get_completed_tasks(data.tg_id)
    if data.task_id in completed:
        raise HTTPException(status_code=400, detail="Задание уже выполнено")
        
    task_info = config.TASKS[data.task_id]
    chat_id = task_info["chat_id"]
    
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getChatMember"
    params = {"chat_id": chat_id, "user_id": data.tg_id}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            res_data = response.json()
            
            if res_data.get("ok"):
                status = res_data["result"]["status"]
                if status in ["member", "administrator", "creator"]:
                    await database.mark_task_completed(data.tg_id, data.task_id)
                    await database.add_points_to_user(data.tg_id, task_info["reward"])
                    
                    user_data = await database.get_user_data(data.tg_id)
                    return {"status": "ok", "balance": user_data["balance"]}
                else:
                    return {"status": "error", "detail": "Вы не подписаны на канал!"}
            else:
                return {"status": "error", "detail": "Ошибка проверки. Бот администратор в канале?"}
                
        except Exception as e:
            return {"status": "error", "detail": "Ошибка соединения с Telegram API."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)