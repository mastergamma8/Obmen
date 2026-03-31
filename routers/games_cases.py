from fastapi import APIRouter, Depends, HTTPException
import random
import time

import config
import database
from handlers.models import ActionData
from handlers.security import get_current_user

router = APIRouter(prefix="/cases", tags=["cases"])

FREE_CASE_COOLDOWN = 86400  # 24 часа
CASE_HOUSE_EDGE    = 0.15


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def _get_item_value(item: dict) -> int:
    if item["type"] in ("donuts", "stars"):
        return item.get("amount", 0)
    elif item["type"] == "gift":
        gift_id = item.get("gift_id")
        if gift_id in config.MAIN_GIFTS:
            return config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            return config.BASE_GIFTS[gift_id].get("value", 0)
    return 0


def _roll_item(items: list) -> dict:
    total_chance = sum(item.get("chance", 0) for item in items)
    if total_chance <= 0:
        total_chance = 100
    r = random.uniform(0, total_chance)
    cumulative = 0
    for item in items:
        chance = item.get("chance", 0)
        if chance <= 0:
            continue
        cumulative += chance
        if r <= cumulative:
            return item
    return items[0]


async def _roll_item_bank_aware(items: list, currency: str) -> dict:
    if currency != "stars":
        return _roll_item(items)

    bank_balance = await database.bank_get_max_payout()
    affordable   = [i for i in items if _get_item_value(i) <= bank_balance]
    if not affordable:
        return min(items, key=lambda i: _get_item_value(i))
    return _roll_item(affordable)


async def _apply_win(tg_id: int, win_item: dict, case: dict, price: int):
    if win_item["type"] == "donuts":
        await database.add_points_to_user(tg_id, win_item["amount"])
        await database.add_history_entry(tg_id, "case_win_donuts", "Case — donuts won", win_item["amount"])
        await database.add_history_entry(
            tg_id, "case_lucky_ratio",
            f"Case '{case['name']}' — luck ratio",
            round(win_item["amount"] / max(price, 1) * 100)
        )

    elif win_item["type"] == "stars":
        await database.add_stars_to_user(tg_id, win_item["amount"])
        await database.add_history_entry(tg_id, "case_win_stars", "Case — stars won", win_item["amount"])
        await database.add_history_entry(
            tg_id, "case_lucky_ratio",
            f"Case '{case['name']}' — luck ratio",
            round(win_item["amount"] / max(price, 1) * 100)
        )

    elif win_item["type"] == "gift":
        gift_id    = win_item["gift_id"]
        gift_name  = "Gift"
        gift_value = 0
        if gift_id in config.MAIN_GIFTS:
            gift_name  = config.MAIN_GIFTS[gift_id]["name"]
            gift_value = config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            gift_name  = config.BASE_GIFTS[gift_id]["name"]
            gift_value = config.BASE_GIFTS[gift_id].get("value", 0)

        await database.add_gift_to_user(tg_id, gift_id, 1)
        await database.add_history_entry(tg_id, "case_win_gift", f"Case — gift won: {gift_name}", 0)
        if gift_value > 0 and price > 0:
            await database.add_history_entry(
                tg_id, "case_lucky_ratio",
                f"Case '{case['name']}' — luck ratio (gift)",
                round(gift_value / price * 100)
            )


# ─── Платный кейс ─────────────────────────────────────────────────────────────

@router.post("/open")
async def open_case(data: ActionData, current_user: dict = Depends(get_current_user)):
    tg_id   = current_user["id"]
    case_id = data.gift_id

    if case_id not in config.CASES_CONFIG:
        raise HTTPException(status_code=400, detail="Case not found")

    case     = config.CASES_CONFIG[case_id]
    currency = case.get("currency", "donuts")
    price    = case["price"]

    # Атомарное списание
    if currency == "stars":
        deducted = await database.deduct_stars(tg_id, price)
    else:
        deducted = await database.deduct_balance(tg_id, price)

    if not deducted:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough {'stars' if currency == 'stars' else 'donuts'} to open this case",
        )

    await database.add_history_entry(tg_id, f"case_paid_{currency}",
        f"Case opened: '{case['name']}'", -price)
    await database.bank_deposit(price, CASE_HOUSE_EDGE, asset_type=currency)

    win_item  = await _roll_item_bank_aware(case["items"], currency)
    win_value = _get_item_value(win_item)

    if win_value > 0:
        payout_type = "gift_value" if win_item["type"] == "gift" else currency
        paid = await database.bank_payout(win_value, asset_type=payout_type)
        if not paid:
            # Банк не смог выплатить — выбираем только предметы, реально доступные банку
            bank_max = await database.bank_get_max_payout(asset_type=currency)
            affordable_items = [i for i in case["items"] if _get_item_value(i) <= bank_max]

            if affordable_items:
                win_item    = min(affordable_items, key=lambda i: _get_item_value(i))
                win_value   = _get_item_value(win_item)
                payout_type = "gift_value" if win_item["type"] == "gift" else currency
                if win_value > 0:
                    fallback_paid = await database.bank_payout(win_value, asset_type=payout_type)
                    if not fallback_paid:
                        # Даже дешевейший предмет не прошёл — не выдаём ничего
                        await database.add_history_entry(
                            tg_id, "case_bank_empty",
                            f"Case '{case['name']}' — банк исчерпан, приз не выдан", 0
                        )
                        updated_user  = await database.get_user_data(tg_id)
                        updated_gifts = await database.get_user_gifts(tg_id)
                        return {
                            "status":     "bank_empty",
                            "win_item":   None,
                            "balance":    updated_user["balance"],
                            "stars":      updated_user["stars"],
                            "user_gifts": updated_gifts,
                        }
                # else: win_value == 0 (бесплатный предмет), продолжаем выдачу
            else:
                # Вообще нет доступных предметов — ничего не выдаём
                await database.add_history_entry(
                    tg_id, "case_bank_empty",
                    f"Case '{case['name']}' — банк исчерпан, приз не выдан", 0
                )
                updated_user  = await database.get_user_data(tg_id)
                updated_gifts = await database.get_user_gifts(tg_id)
                return {
                    "status":     "bank_empty",
                    "win_item":   None,
                    "balance":    updated_user["balance"],
                    "stars":      updated_user["stars"],
                    "user_gifts": updated_gifts,
                }

    await _apply_win(tg_id, win_item, case, price)

    updated_user  = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)

    return {
        "status":     "ok",
        "win_item":   win_item,
        "balance":    updated_user["balance"],
        "stars":      updated_user["stars"],
        "user_gifts": updated_gifts,
    }


# ─── Бесплатный кейс (раз в 24 ч) ────────────────────────────────────────────

@router.get("/free_status")
async def free_case_status(current_user: dict = Depends(get_current_user)):
    tg_id     = current_user["id"]
    last      = await database.get_last_free_case(tg_id)
    now       = int(time.time())
    remaining = max(0, FREE_CASE_COOLDOWN - (now - last))
    return {"remaining_seconds": remaining, "available": remaining == 0}


@router.post("/open_free")
async def open_free_case(current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]

    if not hasattr(config, "FREE_CASE_CONFIG"):
        raise HTTPException(status_code=503, detail="Free case is not configured")

    now       = int(time.time())
    last      = await database.get_last_free_case(tg_id)
    remaining = FREE_CASE_COOLDOWN - (now - last)

    if remaining > 0:
        hours   = remaining // 3600
        minutes = (remaining % 3600) // 60
        raise HTTPException(
            status_code=429,
            detail=f"Free case available in {hours}h {minutes}m",
        )

    case     = config.FREE_CASE_CONFIG
    win_item = _roll_item(case["items"])

    await database.update_last_free_case(tg_id, now)
    await database.add_history_entry(tg_id, "case_free_open",
        f"Free case opened: '{case['name']}'", 0)
    await _apply_win(tg_id, win_item, case, price=0)

    updated_user  = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)

    return {
        "status":       "ok",
        "win_item":     win_item,
        "balance":      updated_user["balance"],
        "stars":        updated_user["stars"],
        "user_gifts":   updated_gifts,
        "next_free_in": FREE_CASE_COOLDOWN,
    }
