from fastapi import APIRouter, Depends, HTTPException
import time
import random

import config
import database
from handlers.tg_gifts import get_gift_def, get_gift_value, is_real_tg_gift
from handlers.models import SpinData
from handlers.security import get_current_user

router = APIRouter(prefix="/roulette", tags=["roulette"])

ROULETTE_HOUSE_EDGE = 0.15


def _get_item_value(item: dict) -> int:
    if item["type"] in ("donuts", "stars"):
        return item.get("amount", 0)
    if item["type"] == "gift":
        return get_gift_value(item.get("gift_id"))
    return 0


def _roll_item(items: list) -> tuple[int, dict]:
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
    bank_liquidity = await database.bank_get_max_payout()
    affordable = [item for item in items if _get_item_value(item) <= bank_liquidity]

    if not affordable:
        cheapest = min(items, key=lambda i: _get_item_value(i))
        return items.index(cheapest), cheapest

    idx_in_affordable, win_item = _roll_item(affordable)
    real_idx = items.index(win_item)
    return real_idx, win_item


@router.get("/info")
async def get_roulette_info(current_user: dict = Depends(get_current_user)):
    tg_id     = current_user["id"]
    user_data = await database.get_user_data(tg_id)
    last_spin = user_data.get("last_free_spin", 0)
    now       = int(time.time())
    can_free  = (now - last_spin) >= 86400

    return {
        "status":   "ok",
        "can_free": can_free,
        "cost":     config.ROULETTE_CONFIG["cost"],
        "currency": config.ROULETTE_CONFIG.get("currency", "donuts"),
        "items":    config.ROULETTE_CONFIG["items"],
        "time_left": 86400 - (now - last_spin) if not can_free else 0,
    }


@router.post("/spin")
async def spin_roulette(data: SpinData, current_user: dict = Depends(get_current_user)):
    tg_id     = current_user["id"]
    user_data = await database.get_user_data(tg_id)
    last_spin = user_data.get("last_free_spin", 0)
    now       = int(time.time())
    can_free  = (now - last_spin) >= 86400

    currency = config.ROULETTE_CONFIG.get("currency", "donuts")
    cost     = config.ROULETTE_CONFIG["cost"]

    if can_free:
        await database.update_last_free_spin(tg_id, now)
    else:
        # Атомарное списание
        if currency == "stars":
            deducted = await database.deduct_stars(tg_id, cost)
        else:
            deducted = await database.deduct_balance(tg_id, cost)

        if not deducted:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'} для прокрутки",
            )

        await database.add_history_entry(
            tg_id, f"roulette_paid_{currency}",
            f"Платная прокрутка рулетки (-{cost} {currency})", -cost
        )
        await database.bank_deposit(cost, ROULETTE_HOUSE_EDGE, asset_type=currency)

    items = config.ROULETTE_CONFIG["items"]

    if can_free:
        win_index = next(
            (i for i, item in enumerate(items)
             if item.get("type") == "stars" and item.get("amount") == 1),
            0
        )
        win_item = items[win_index]
    else:
        win_index, win_item = await _roll_item_bank_aware(items, currency)

    spin_type = "Бесплатная прокрутка рулетки" if can_free else "Прокрутка рулетки"

    if win_item["type"] == "donuts":
        prize_value = win_item["amount"]
        if not can_free:
            # Используем bank_payout как финальную проверку (пункт 6)
            paid = await database.bank_payout(prize_value, asset_type="donuts")
            if not paid:
                # Fallback — выдаём 1 звезду (самый дешёвый приз)
                fallback = next((i for i in items if i.get("type") == "stars" and i.get("amount") == 1), None)
                if fallback:
                    win_item  = fallback
                    win_index = items.index(fallback)
                    await database.add_stars_to_user(tg_id, 1)
                    await database.add_history_entry(tg_id, "roulette_win_stars",
                        f"{spin_type} — fallback (банк пуст)", 1)
                    updated_user  = await database.get_user_data(tg_id)
                    updated_gifts = await database.get_user_gifts(tg_id)
                    return _build_spin_response(win_index, win_item, updated_user, updated_gifts)
        await database.add_points_to_user(tg_id, prize_value)
        await database.add_history_entry(tg_id, "roulette_win_donuts",
            f"{spin_type} — выиграно пончиков", prize_value)

    elif win_item["type"] == "stars":
        prize_value = win_item["amount"]
        if not can_free:
            paid = await database.bank_payout(prize_value, asset_type="stars")
            if not paid:
                fallback = min(items, key=_get_item_value)
                win_item  = fallback
                win_index = items.index(fallback)
                prize_value = _get_item_value(fallback)
                await database.add_stars_to_user(tg_id, max(prize_value, 1))
                await database.add_history_entry(tg_id, "roulette_win_stars",
                    f"{spin_type} — fallback (банк пуст)", max(prize_value, 1))
                updated_user  = await database.get_user_data(tg_id)
                updated_gifts = await database.get_user_gifts(tg_id)
                return _build_spin_response(win_index, win_item, updated_user, updated_gifts)
        await database.add_stars_to_user(tg_id, prize_value)
        await database.add_history_entry(tg_id, "roulette_win_stars",
            f"{spin_type} — выиграно звезд", prize_value)

    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        gift_def = get_gift_def(gift_id)
        gift_name = gift_def["name"] if gift_def else "Подарок"
        gift_value = get_gift_value(gift_id)

        if not can_free and gift_value > 0:
            paid = await database.bank_payout(gift_value, asset_type="gift_value")
            if not paid:
                # Банк не потянул — заменяем на самый дешёвый нон-гифт приз
                fallback_items = [i for i in items if i["type"] != "gift"]
                if fallback_items:
                    _, win_item = _roll_item(fallback_items)
                    win_index = items.index(win_item)
                    ptype = win_item["type"]
                    fv = win_item["amount"]
                    if ptype == "stars":
                        await database.add_stars_to_user(tg_id, fv)
                    else:
                        await database.add_points_to_user(tg_id, fv)
                    await database.add_history_entry(tg_id, f"roulette_win_{ptype}",
                        f"{spin_type} — замена подарка (банк пуст)", fv)
                    updated_user = await database.get_user_data(tg_id)
                    updated_gifts = await database.get_user_gifts(tg_id)
                    return _build_spin_response(win_index, win_item, updated_user, updated_gifts)

        await database.add_gift_to_user(tg_id, gift_id, 1)
        if gift_def and is_real_tg_gift(gift_id):
            await database.add_history_entry(tg_id, "roulette_win_tg_gift",
                f"{spin_type} — Telegram gift won: {gift_name}", 0)
        else:
            await database.add_history_entry(tg_id, "roulette_win_gift",
                f"{spin_type} — выигран подарок: {gift_name}", 0)

    updated_user  = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)
    return _build_spin_response(win_index, win_item, updated_user, updated_gifts)


def _build_spin_response(win_index, win_item, updated_user, updated_gifts):
    return {
        "status":       "ok",
        "win_index":    win_index,
        "win_item":     win_item,
        "balance":      updated_user["balance"],
        "stars":        updated_user["stars"],
        "user_gifts":   updated_gifts,
        "can_free_now": False,
    }
