from fastapi import APIRouter, Depends, HTTPException
import random

import config
import database
from models import ActionData
from security import verify_user

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/open")
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
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'} для покупки"
        )

    if currency == "stars":
        await database.add_stars_to_user(data.tg_id, -price)
    else:
        await database.add_points_to_user(data.tg_id, -price)

    await database.add_history_entry(
        data.tg_id, f"case_paid_{currency}",
        f"Открытие кейса '{case['name']}'", -price
    )

    items = case["items"]
    total_chance = sum(item.get("chance", 0) for item in items)
    if total_chance <= 0:
        total_chance = 100

    r = random.uniform(0, total_chance)
    cumulative, win_index = 0, 0

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
        await database.add_history_entry(
            data.tg_id, "case_win_donuts",
            "Кейс — выиграно пончиков", win_item["amount"]
        )
        # Коэффициент удачи для рейтинга «Счастливчики» (int: ratio * 100)
        lucky_ratio_x100 = round(win_item["amount"] / price * 100)
        await database.add_history_entry(
            data.tg_id, "case_lucky_ratio",
            f"Кейс '{case['name']}' — коэффициент удачи", lucky_ratio_x100
        )
    elif win_item["type"] == "stars":
        await database.add_stars_to_user(data.tg_id, win_item["amount"])
        await database.add_history_entry(
            data.tg_id, "case_win_stars",
            "Кейс — выиграно звезд", win_item["amount"]
        )
        lucky_ratio_x100 = round(win_item["amount"] / price * 100)
        await database.add_history_entry(
            data.tg_id, "case_lucky_ratio",
            f"Кейс '{case['name']}' — коэффициент удачи", lucky_ratio_x100
        )
    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        await database.add_gift_to_user(data.tg_id, gift_id, 1)

        gift_name = "Подарок"
        gift_value = 0
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
            gift_value = config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]
            gift_value = config.BASE_GIFTS[gift_id].get("value", 0)

        await database.add_history_entry(
            data.tg_id, "case_win_gift",
            f"Кейс — выигран подарок: {gift_name}", 0
        )
        if gift_value > 0:
            lucky_ratio_x100 = round(gift_value / price * 100)
            await database.add_history_entry(
                data.tg_id, "case_lucky_ratio",
                f"Кейс '{case['name']}' — коэффициент удачи (подарок)", lucky_ratio_x100
            )

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)

    return {
        "status": "ok",
        "win_item": win_item,
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "user_gifts": updated_gifts
    }
