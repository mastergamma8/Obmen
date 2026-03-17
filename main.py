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
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return calculated_hash == hash_
    except Exception:
        return False

async def verify_user(x_tg_data: str = Header(None)):
    if not config.BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Токен бота не настроен")
    if x_tg_data and not validate_telegram_data(x_tg_data):
        print(f"[AUTH WARNING] Telegram initData validation failed (len={len(x_tg_data)})")
    return True
# ------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

os.makedirs("gifts", exist_ok=True)
app.mount("/gifts", StaticFiles(directory="gifts"), name="gifts")
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

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
            "roulette": config.ROULETTE_CONFIG,
            "cases": config.CASES_CONFIG 
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
    
    gift_name = config.MAIN_GIFTS[data.gift_id]["name"]
    await database.add_history_entry(
        data.tg_id, "claim_gift", f"Куплен подарок: {gift_name}", -cost
    )
        
    user_data = await database.get_user_data(data.tg_id)
    user_gifts = await database.get_user_gifts(data.tg_id)
    return {"status": "ok", "balance": user_data["balance"], "user_gifts": user_gifts}

@app.post("/api/withdraw")
async def withdraw_gift(data: ActionData, is_valid: bool = Depends(verify_user)):
    user_gifts = await database.get_user_gifts(data.tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")
        
    await database.remove_gift_from_user(data.tg_id, data.gift_id)
    
    gift_name_for_history = "Подарок"
    if data.gift_id in config.MAIN_GIFTS:
        gift_name_for_history = config.MAIN_GIFTS[data.gift_id]["name"]
    elif data.gift_id in config.BASE_GIFTS:
        gift_name_for_history = config.BASE_GIFTS[data.gift_id]["name"]
    await database.add_history_entry(
        data.tg_id, "withdraw_gift", f"Вывод подарка: {gift_name_for_history}", 0
    )
    
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

@app.get("/api/history")
async def get_history(tg_id: int, is_valid: bool = Depends(verify_user)):
    history = await database.get_user_history(tg_id)
    return {"history": history}

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
        await database.add_history_entry(
            data.tg_id, "roulette_paid", "Платная прокрутка рулетки", -cost
        )

    items = config.ROULETTE_CONFIG["items"]
    
    if can_free:
        win_index = 0
        for i, item in enumerate(items):
            if item.get("type") == "donuts" and item.get("amount") == 1:
                win_index = i
                break
        win_item = items[win_index]
    else:
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
        if can_free:
            await database.add_history_entry(
                data.tg_id, "roulette_free", "Бесплатная прокрутка рулетки", win_item["amount"]
            )
        else:
            await database.add_history_entry(
                data.tg_id, "roulette_win_donuts", "Прокрутка рулетки — выиграно пончиков", win_item["amount"]
            )
    elif win_item["type"] == "gift":
        await database.add_gift_to_user(data.tg_id, win_item["gift_id"], 1)
        gift_id = win_item["gift_id"]
        gift_name = "Подарок"
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]
        if can_free:
            await database.add_history_entry(
                data.tg_id, "roulette_free_gift", f"Бесплатная рулетка — подарок: {gift_name}", 0
            )
        else:
            await database.add_history_entry(
                data.tg_id, "roulette_win_gift", f"Прокрутка рулетки — подарок: {gift_name}", 0
            )

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

@app.post("/api/cases/open")
async def open_case(data: ActionData, is_valid: bool = Depends(verify_user)):
    case_id = data.gift_id 
    if case_id not in config.CASES_CONFIG:
        raise HTTPException(status_code=400, detail="Кейс не найден")

    case = config.CASES_CONFIG[case_id]
    user_data = await database.get_user_data(data.tg_id)

    if user_data["balance"] < case["price"]:
        raise HTTPException(status_code=400, detail="Недостаточно пончиков")

    await database.add_points_to_user(data.tg_id, -case["price"])
    await database.add_history_entry(data.tg_id, "case_open", f"Открыт кейс: {case['name']}", -case["price"])

    items = case["items"]
    total_chance = sum(item.get("chance", 0) for item in items)
    if total_chance <= 0:
        total_chance = 100
        
    r = random.uniform(0, total_chance)
    cumulative = 0
    win_index = 0

    for i, item in enumerate(items):
        chance = item.get("chance", 0)
        if chance <= 0: continue
        cumulative += chance
        if r <= cumulative:
            win_index = i
            break

    win_item = items[win_index]

    if win_item["type"] == "donuts":
        await database.add_points_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(data.tg_id, "case_win_donuts", f"Кейс '{case['name']}' — выиграно пончиков", win_item["amount"])
    elif win_item["type"] == "gift":
        await database.add_gift_to_user(data.tg_id, win_item["gift_id"], 1)
        # В кейсах логика определения имени уже была правильной
        gift_name = config.BASE_GIFTS.get(win_item["gift_id"], {}).get("name", "Подарок")
        if win_item["gift_id"] in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[win_item["gift_id"]]["name"]
        await database.add_history_entry(data.tg_id, "case_win_gift", f"Кейс '{case['name']}' — выигран подарок: {gift_name}", 0)

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)

    return {
        "status": "ok",
        "win_item": win_item,
        "balance": updated_user["balance"],
        "user_gifts": updated_gifts
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
            "url": t_data.get("url", ""), 
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
    task_type = task_info.get("type", "subscription") 
    
    success_status = False

    if task_type == "referral":
        required_refs = task_info.get("required_referrals", 1)
        referrals = await database.get_referrals(data.tg_id)
        
        if len(referrals) >= required_refs:
            success_status = True
        else:
            remaining = required_refs - len(referrals)
            return {"status": "error", "detail": f"Вам нужно пригласить еще {remaining} чел. (Приглашено: {len(referrals)})"}
    
    else:
        chat_id = task_info.get("chat_id")
        async with httpx.AsyncClient() as client:
            try:
                if task_type == "subscription":
                    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getChatMember"
                    params = {"chat_id": chat_id, "user_id": data.tg_id}
                    
                    response = await client.get(url, params=params)
                    res_data = response.json()
                    
                    if res_data.get("ok"):
                        status = res_data["result"]["status"]
                        if status in ["member", "administrator", "creator"]:
                            success_status = True
                        else:
                            return {"status": "error", "detail": "Вы не подписаны на канал!"}
                    else:
                        return {"status": "error", "detail": "Ошибка проверки. Бот администратор в канале?"}
                
                elif task_type == "boost":
                    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUserChatBoosts"
                    params = {"chat_id": chat_id, "user_id": data.tg_id}
                    
                    response = await client.get(url, params=params)
                    res_data = response.json()
                    
                    if res_data.get("ok"):
                        boosts = res_data["result"]["boosts"]
                        if len(boosts) > 0:
                            success_status = True
                        else:
                            return {"status": "error", "detail": "Вы не проголосовали за канал (нет активного буста)!"}
                    else:
                        return {"status": "error", "detail": "Ошибка проверки буста. Бот администратор в канале?"}
                else:
                    return {"status": "error", "detail": "Неизвестный тип задания."}

            except Exception as e:
                return {"status": "error", "detail": f"Ошибка соединения с Telegram API: {str(e)}"}

    if success_status:
        await database.mark_task_completed(data.tg_id, data.task_id)
        await database.add_points_to_user(data.tg_id, task_info["reward"])
        await database.add_history_entry(
            data.tg_id, "task_reward", f"Задание выполнено: {task_info['title']}", task_info["reward"]
        )
        
        user_data = await database.get_user_data(data.tg_id)
        return {"status": "ok", "balance": user_data["balance"]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)