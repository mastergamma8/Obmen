from fastapi import APIRouter, Depends, HTTPException
import time
import random

import config
import database
from models import SpinData, ActionData, RocketBetData, RocketCashoutData
from security import verify_user

router = APIRouter(prefix="/api", tags=["games"])

# Глобальное состояние для активных игр в ракету
active_rocket_games = {}

@router.get("/roulette/info")
async def get_roulette_info(tg_id: int, is_valid: bool = Depends(verify_user)):
    user_data = await database.get_user_data(tg_id)
    last_spin = user_data.get("last_free_spin", 0)
    now = int(time.time())
    can_free = (now - last_spin) >= 86400 
    
    return {
        "status": "ok",
        "can_free": can_free,
        "cost": config.ROULETTE_CONFIG["cost"],
        "currency": config.ROULETTE_CONFIG.get("currency", "donuts"),
        "items": config.ROULETTE_CONFIG["items"],
        "time_left": 86400 - (now - last_spin) if not can_free else 0
    }

@router.post("/roulette/spin")
async def spin_roulette(data: SpinData, is_valid: bool = Depends(verify_user)):
    user_data = await database.get_user_data(data.tg_id)
    last_spin = user_data.get("last_free_spin", 0)
    now = int(time.time())
    can_free = (now - last_spin) >= 86400

    currency = config.ROULETTE_CONFIG.get("currency", "donuts")
    cost = config.ROULETTE_CONFIG["cost"]

    if can_free:
        await database.update_last_free_spin(data.tg_id, now)
    else:
        user_balance = user_data["stars"] if currency == "stars" else user_data["balance"]
        if user_balance < cost:
            raise HTTPException(status_code=400, detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'} для прокрутки")
            
        if currency == "stars":
            await database.add_stars_to_user(data.tg_id, -cost)
        else:
            await database.add_points_to_user(data.tg_id, -cost)
            
        await database.add_history_entry(data.tg_id, f"roulette_paid_{currency}", f"Платная прокрутка рулетки (-{cost} {currency})", -cost)

    items = config.ROULETTE_CONFIG["items"]
    
    if can_free:
        # Изменено: теперь ищем элемент, у которого тип "stars" и количество 1
        win_index = next((i for i, item in enumerate(items) if item.get("type") == "stars" and item.get("amount") == 1), 0)
        win_item = items[win_index]
    else:
        total_chance = sum(item.get("chance", 0) for item in items)
        if total_chance <= 0: total_chance = 100 
            
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
    
    spin_type = "Бесплатная прокрутка рулетки" if can_free else "Прокрутка рулетки"
    
    if win_item["type"] == "donuts":
        await database.add_points_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(data.tg_id, "roulette_win_donuts", f"{spin_type} — выиграно пончиков", win_item["amount"])
    elif win_item["type"] == "stars":
        await database.add_stars_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(data.tg_id, "roulette_win_stars", f"{spin_type} — выиграно звезд", win_item["amount"])
    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        await database.add_gift_to_user(data.tg_id, gift_id, 1)
        
        # Определяем название подарка для истории
        gift_name = "Подарок"
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]
            
        await database.add_history_entry(data.tg_id, "roulette_win_gift", f"{spin_type} — выигран подарок: {gift_name}", 0)

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)
    
    return {
        "status": "ok",
        "win_index": win_index,
        "win_item": win_item,
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "user_gifts": updated_gifts,
        "can_free_now": False 
    }

@router.post("/cases/open")
async def open_case(data: ActionData, is_valid: bool = Depends(verify_user)):
    case_id = data.gift_id 
    if case_id not in config.CASES_CONFIG:
        raise HTTPException(status_code=400, detail="Кейс не найден")

    case = config.CASES_CONFIG[case_id]
    currency = case.get("currency", "donuts")
    price = case["price"]
    user_data = await database.get_user_data(data.tg_id)

    user_balance = user_data["stars"] if currency == "stars" else user_data["balance"]
    if user_balance < price:
        raise HTTPException(status_code=400, detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'} для покупки")

    if currency == "stars":
        await database.add_stars_to_user(data.tg_id, -price)
    else:
        await database.add_points_to_user(data.tg_id, -price)
        
    await database.add_history_entry(data.tg_id, f"case_paid_{currency}", f"Открытие кейса '{case['name']}'", -price)

    items = case["items"]
    total_chance = sum(item.get("chance", 0) for item in items)
    if total_chance <= 0: total_chance = 100
        
    r = random.uniform(0, total_chance)
    cumulative, win_index = 0, 0

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
        await database.add_history_entry(data.tg_id, "case_win_donuts", f"Кейс — выиграно пончиков", win_item["amount"])
        # Записываем коэффициент удачи для рейтинга «Счастливчики»
        # Храним как int: ratio * 100, чтобы уложиться в INTEGER-колонку
        lucky_ratio_x100 = round(win_item["amount"] / price * 100)
        await database.add_history_entry(data.tg_id, "case_lucky_ratio", f"Кейс '{case['name']}' — коэффициент удачи", lucky_ratio_x100)
    elif win_item["type"] == "stars":
        await database.add_stars_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(data.tg_id, "case_win_stars", f"Кейс — выиграно звезд", win_item["amount"])
        # Звёзды тоже считаем как выигрыш
        lucky_ratio_x100 = round(win_item["amount"] / price * 100)
        await database.add_history_entry(data.tg_id, "case_lucky_ratio", f"Кейс '{case['name']}' — коэффициент удачи", lucky_ratio_x100)
    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        await database.add_gift_to_user(data.tg_id, gift_id, 1)
        
        # Ищем название подарка как в главных, так и в базовых
        gift_name = "Подарок"
        gift_value = 0
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
            gift_value = config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]
            gift_value = config.BASE_GIFTS[gift_id].get("value", 0)
            
        await database.add_history_entry(data.tg_id, "case_win_gift", f"Кейс — выигран подарок: {gift_name}", 0)
        # Если у подарка есть цена в конфиге — тоже учитываем в рейтинге
        if gift_value > 0:
            lucky_ratio_x100 = round(gift_value / price * 100)
            await database.add_history_entry(data.tg_id, "case_lucky_ratio", f"Кейс '{case['name']}' — коэффициент удачи (подарок)", lucky_ratio_x100)

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)

    return {
        "status": "ok",
        "win_item": win_item,
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "user_gifts": updated_gifts
    }

@router.post("/rocket/start")
async def start_rocket(data: RocketBetData, is_valid: bool = Depends(verify_user)):
    user_data = await database.get_user_data(data.tg_id)
    bet = data.bet
    currency = config.ROCKET_CONFIG.get("currency", "donuts")
    
    if bet < config.ROCKET_CONFIG["min_bet"] or bet > config.ROCKET_CONFIG["max_bet"]:
        raise HTTPException(status_code=400, detail="Неверная сумма ставки")
        
    user_balance = user_data["stars"] if currency == "stars" else user_data["balance"]
    if user_balance < bet:
        raise HTTPException(status_code=400, detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'}")
        
    if currency == "stars":
        await database.add_stars_to_user(data.tg_id, -bet)
    else:
        await database.add_points_to_user(data.tg_id, -bet)
    
    r = random.uniform(0, 1)
    if r < config.ROCKET_CONFIG["house_edge"]:
        crash_point = 1.00
    else:
        crash_point = round(0.95 / (1.0 - r), 2)
        
    if crash_point > config.ROCKET_CONFIG["max_multiplier"]:
        crash_point = config.ROCKET_CONFIG["max_multiplier"]
        
    active_rocket_games[data.tg_id] = {
        "bet": bet,
        "currency": currency,
        "crash_point": crash_point
    }
    
    updated_user = await database.get_user_data(data.tg_id)
    
    return {
        "status": "ok",
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "crash_point": crash_point
    }

@router.post("/rocket/cashout")
async def cashout_rocket(data: RocketCashoutData, is_valid: bool = Depends(verify_user)):
    if data.tg_id not in active_rocket_games:
        raise HTTPException(status_code=400, detail="Активная игра не найдена или уже завершена")
        
    game = active_rocket_games.pop(data.tg_id)
    currency = game.get("currency", "donuts")
    
    if data.multiplier <= game["crash_point"]:
        win_amount = int(game["bet"] * data.multiplier)
        
        if currency == "stars":
            await database.add_stars_to_user(data.tg_id, win_amount)
        else:
            await database.add_points_to_user(data.tg_id, win_amount)
        
        await database.add_history_entry(
            data.tg_id, f"rocket_win_{currency}", f"Ракета (x{data.multiplier:.2f})", win_amount - game["bet"]
        )
        
        updated_user = await database.get_user_data(data.tg_id)
        return {
            "status": "ok",
            "win_amount": win_amount,
            "balance": updated_user["balance"],
            "stars": updated_user["stars"]
        }
    else:
        await database.add_history_entry(data.tg_id, f"rocket_lose_{currency}", f"Ракета проигрыш", -game["bet"])
        updated_user = await database.get_user_data(data.tg_id)
        return {
            "status": "error",
            "detail": "Ракета уже улетела!",
            "balance": updated_user["balance"],
            "stars": updated_user["stars"]
        }
@router.post("/rocket/crash")
async def crash_rocket(data: RocketBetData, is_valid: bool = Depends(verify_user)):
    """Вызывается фронтендом когда ракета улетела и игрок не успел забрать."""
    game = active_rocket_games.pop(data.tg_id, None)
    if not game:
        # Игра уже закрыта (например игрок успел сделать cashout в последний момент)
        return {"status": "ok", "already_closed": True}

    currency = game.get("currency", "donuts")

    await database.add_history_entry(
        data.tg_id, f"rocket_lose_{currency}",
        f"Ракета улетела на x{game['crash_point']:.2f} (ставка: {game['bet']})", -game["bet"]
    )

    updated_user = await database.get_user_data(data.tg_id)
    return {
        "status": "ok",
        "balance": updated_user["balance"],
        "stars": updated_user["stars"]
    }