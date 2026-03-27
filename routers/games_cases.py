from fastapi import APIRouter, Depends, HTTPException
import random
import time

import config
import database
from models import ActionData
from security import verify_user

router = APIRouter(prefix="/cases", tags=["cases"])

FREE_CASE_COOLDOWN = 86400  # 24 hours in seconds

# ─── Shared roll logic ────────────────────────────────────────────────────────

def _roll_item(items: list) -> dict:
    """Pick a random item from a weighted list."""
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


async def _apply_win(tg_id: int, win_item: dict, case: dict, price: int):
    """Credit the win reward to the user and log it."""
    if win_item["type"] == "donuts":
        await database.add_points_to_user(tg_id, win_item["amount"])
        await database.add_history_entry(
            tg_id, "case_win_donuts",
            "Case — donuts won", win_item["amount"]
        )
        lucky_ratio_x100 = round(win_item["amount"] / max(price, 1) * 100)
        await database.add_history_entry(
            tg_id, "case_lucky_ratio",
            f"Case '{case['name']}' — luck ratio", lucky_ratio_x100
        )

    elif win_item["type"] == "stars":
        await database.add_stars_to_user(tg_id, win_item["amount"])
        await database.add_history_entry(
            tg_id, "case_win_stars",
            "Case — stars won", win_item["amount"]
        )
        lucky_ratio_x100 = round(win_item["amount"] / max(price, 1) * 100)
        await database.add_history_entry(
            tg_id, "case_lucky_ratio",
            f"Case '{case['name']}' — luck ratio", lucky_ratio_x100
        )

    elif win_item["type"] == "gift":
        gift_id = win_item["gift_id"]
        await database.add_gift_to_user(tg_id, gift_id, 1)

        gift_name = "Gift"
        gift_value = 0
        if gift_id in config.MAIN_GIFTS:
            gift_name = config.MAIN_GIFTS[gift_id]["name"]
            gift_value = config.MAIN_GIFTS[gift_id].get("required_value", 0)
        elif gift_id in config.BASE_GIFTS:
            gift_name = config.BASE_GIFTS[gift_id]["name"]
            gift_value = config.BASE_GIFTS[gift_id].get("value", 0)

        await database.add_history_entry(
            tg_id, "case_win_gift",
            f"Case — gift won: {gift_name}", 0
        )
        if gift_value > 0 and price > 0:
            lucky_ratio_x100 = round(gift_value / price * 100)
            await database.add_history_entry(
                tg_id, "case_lucky_ratio",
                f"Case '{case['name']}' — luck ratio (gift)", lucky_ratio_x100
            )


# ─── Paid case ────────────────────────────────────────────────────────────────

@router.post("/open")
async def open_case(data: ActionData, is_valid: bool = Depends(verify_user)):
    case_id = data.gift_id
    if case_id not in config.CASES_CONFIG:
        raise HTTPException(status_code=400, detail="Case not found")

    case = config.CASES_CONFIG[case_id]
    currency = case.get("currency", "donuts")
    price = case["price"]
    user_data = await database.get_user_data(data.tg_id)

    user_balance = user_data["stars"] if currency == "stars" else user_data["balance"]
    if user_balance < price:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough {'stars' if currency == 'stars' else 'donuts'} to open this case"
        )

    if currency == "stars":
        await database.add_stars_to_user(data.tg_id, -price)
    else:
        await database.add_points_to_user(data.tg_id, -price)

    await database.add_history_entry(
        data.tg_id, f"case_paid_{currency}",
        f"Case opened: '{case['name']}'", -price
    )

    win_item = _roll_item(case["items"])
    await _apply_win(data.tg_id, win_item, case, price)

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)

    return {
        "status": "ok",
        "win_item": win_item,
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "user_gifts": updated_gifts
    }


# ─── Free case (once per 24 h) ────────────────────────────────────────────────

@router.get("/free_status")
async def free_case_status(tg_id: int):
    """Return how many seconds remain until the free case is available again."""
    last = await database.get_last_free_case(tg_id)
    now = int(time.time())
    remaining = max(0, FREE_CASE_COOLDOWN - (now - last))
    return {"remaining_seconds": remaining, "available": remaining == 0}


@router.post("/open_free")
async def open_free_case(data: ActionData, is_valid: bool = Depends(verify_user)):
    """Open the daily free case. No cost; uses FREE_CASE_CONFIG from config."""
    if not hasattr(config, "FREE_CASE_CONFIG"):
        raise HTTPException(status_code=503, detail="Free case is not configured")

    now = int(time.time())
    last = await database.get_last_free_case(data.tg_id)
    remaining = FREE_CASE_COOLDOWN - (now - last)

    if remaining > 0:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        raise HTTPException(
            status_code=429,
            detail=f"Free case available in {hours}h {minutes}m"
        )

    case = config.FREE_CASE_CONFIG
    win_item = _roll_item(case["items"])

    # Record the usage timestamp BEFORE awarding (prevents double-claim on error)
    await database.update_last_free_case(data.tg_id, now)

    await database.add_history_entry(
        data.tg_id, "case_free_open",
        f"Free case opened: '{case['name']}'", 0
    )
    await _apply_win(data.tg_id, win_item, case, price=0)

    updated_user = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)

    return {
        "status": "ok",
        "win_item": win_item,
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "user_gifts": updated_gifts,
        "next_free_in": FREE_CASE_COOLDOWN
    }