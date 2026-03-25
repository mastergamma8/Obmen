from fastapi import APIRouter, Depends, HTTPException
import time
import random

import config
import database
from models import SpinData
from security import verify_user

router = APIRouter(prefix="/roulette", tags=["roulette"])


@router.get("/info")
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


@router.post("/spin")
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
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'} для прокрутки"
            )

        if currency == "stars":
            await database.add_stars_to_user(data.tg_id, -cost)
        else:
            await database.add_points_to_user(data.tg_id, -cost)

        await database.add_history_entry(
            data.tg_id,
            f"roulette_paid_{currency}",
            f"Платная прокрутка рулетки (-{cost} {currency})",
            -cost
        )

    items = config.ROULETTE_CONFIG["items"]

    if can_free:
        # При бесплатной прокрутке всегда выдаём элемент с типом "stars" и количеством 1
        win_index = next(
            (i for i, item in enumerate(items) if item.get("type") == "stars" and item.get("amount") == 1),
            0
        )
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

    spin_type = "Бесплатная прокрутка рулетки" if can_free else "Прокрутка рулетки"

    if win_item["type"] == "donuts":
        await database.add_points_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(
            data.tg_id, "roulette_win_donuts",
            f"{spin_type} — выиграно пончиков", win_item["amount"]
        )
    elif win_item["type"] == "stars":
        await database.add_stars_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(
            data.tg_id, "roulette_win_stars",
            f"{spin_type} — выиграно звезд", win_item["amount"]
        )
    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        await database.add_gift_to_user(data.tg_id, gift_id, 1)

        gift_name = "Подарок"
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]

        await database.add_history_entry(
            data.tg_id, "roulette_win_gift",
            f"{spin_type} — выигран подарок: {gift_name}", 0
        )

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
