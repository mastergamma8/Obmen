from fastapi import APIRouter, Depends, HTTPException
import time
import random

import config
import database
from models import SpinData
from security import verify_user

router = APIRouter(prefix="/roulette", tags=["roulette"])

# House Edge для рулетки
ROULETTE_HOUSE_EDGE = 0.15  # 15% комиссии казино


def _get_item_value(item: dict) -> int:
    """Возвращает value-эквивалент приза рулетки."""
    if item["type"] in ("donuts", "stars"):
        return item.get("amount", 0)
    elif item["type"] == "gift":
        gift_id = item.get("gift_id")
        if gift_id in config.MAIN_GIFTS:
            return config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            return config.BASE_GIFTS[gift_id].get("value", 0)
    return 0


def _roll_item(items: list) -> tuple[int, dict]:
    """Случайный выбор предмета по весам (chance). Возвращает (index, item)."""
    total_chance = sum(item.get("chance", 0) for item in items)
    if total_chance <= 0:
        total_chance = 100
    r = random.uniform(0, total_chance)
    cumulative = 0
    for i, item in enumerate(items):
        chance = item.get("chance", 0)
        if chance <= 0:
            continue
        cumulative += chance
        if r <= cumulative:
            return i, item
    return 0, items[0]


async def _roll_item_bank_aware(items: list, currency: str) -> tuple[int, dict]:
    """
    Выбирает приз с учётом ликвидности банка.

    Фильтруем призы, чья стоимость превышает суммарный банк.
    Если все дорогие призы недоступны — берём самый дешёвый.
    """
    bank_liquidity = await database.bank_get_max_payout()
    affordable = [item for item in items if _get_item_value(item) <= bank_liquidity]

    if not affordable:
        cheapest = min(items, key=lambda i: _get_item_value(i))
        idx = items.index(cheapest)
        return idx, cheapest

    idx_in_affordable, win_item = _roll_item(affordable)
    # Находим реальный индекс в оригинальном списке
    real_idx = items.index(win_item)
    return real_idx, win_item


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

        # Платная прокрутка — часть стоимости идёт в банк
        await database.bank_deposit(cost, ROULETTE_HOUSE_EDGE, asset_type=currency)

    items = config.ROULETTE_CONFIG["items"]

    if can_free:
        # При бесплатной прокрутке всегда выдаём 1 звезду (не затрагивает банк)
        win_index = next(
            (i for i, item in enumerate(items)
             if item.get("type") == "stars" and item.get("amount") == 1),
            0
        )
        win_item = items[win_index]
    else:
        # Платная прокрутка — приз ограничен банком
        win_index, win_item = await _roll_item_bank_aware(items, currency)

    spin_type = "Бесплатная прокрутка рулетки" if can_free else "Прокрутка рулетки"

    if win_item["type"] == "donuts":
        # Проверяем, может ли банк выплатить пончики
        prize_value = win_item["amount"]
        if not can_free:
            can_pay = await database.bank_can_payout(prize_value, asset_type="donuts")
            if can_pay:
                await database.bank_payout(prize_value, asset_type="donuts")
        await database.add_points_to_user(data.tg_id, prize_value)
        await database.add_history_entry(
            data.tg_id, "roulette_win_donuts",
            f"{spin_type} — выиграно пончиков", prize_value
        )

    elif win_item["type"] == "stars":
        prize_value = win_item["amount"]
        if not can_free:
            can_pay = await database.bank_can_payout(prize_value, asset_type="stars")
            if can_pay:
                await database.bank_payout(prize_value, asset_type="stars")
        await database.add_stars_to_user(data.tg_id, prize_value)
        await database.add_history_entry(
            data.tg_id, "roulette_win_stars",
            f"{spin_type} — выиграно звезд", prize_value
        )

    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        gift_name = "Подарок"
        gift_value = 0
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
            gift_value = config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]
            gift_value = config.BASE_GIFTS[gift_id].get("value", 0)

        # Подарок — списываем его value-эквивалент из банка
        if not can_free and gift_value > 0:
            can_pay = await database.bank_can_payout(gift_value, asset_type="gift_value")
            if not can_pay:
                # Банк не потянет подарок — заменяем на самый дешёвый приз
                fallback_items = [i for i in items if i["type"] != "gift"]
                if fallback_items:
                    win_index, win_item = _roll_item(fallback_items)
                    win_index = items.index(win_item)
                    # Рекурсивно применяем fallback (звёзды или пончики)
                    prize_value = win_item["amount"]
                    ptype = win_item["type"]
                    if not can_free:
                        await database.bank_payout(prize_value, asset_type=ptype)
                    if ptype == "stars":
                        await database.add_stars_to_user(data.tg_id, prize_value)
                    else:
                        await database.add_points_to_user(data.tg_id, prize_value)
                    await database.add_history_entry(
                        data.tg_id, f"roulette_win_{ptype}",
                        f"{spin_type} — выиграно {ptype} (замена подарка)", prize_value
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
            else:
                await database.bank_payout(gift_value, asset_type="gift_value")

        await database.add_gift_to_user(data.tg_id, gift_id, 1)
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
