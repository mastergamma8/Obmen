from fastapi import APIRouter, Depends, HTTPException
import httpx

import config
import database
from handlers.models import TopupData
from handlers.security import get_current_user

router = APIRouter(prefix="/api", tags=["users"])


@router.post("/init")
async def init_user(current_user: dict = Depends(get_current_user)):
    tg_id      = current_user["id"]
    username   = current_user["username"]
    first_name = current_user["first_name"]
    photo_url  = current_user["photo_url"]

    await database.upsert_user(tg_id, username, first_name, photo_url)
    user_data  = await database.get_user_data(tg_id)
    user_gifts = await database.get_user_gifts(tg_id)

    return {
        "status": "ok",
        "balance": user_data.get("balance", 0),
        "stars":   user_data.get("stars", 0),
        "user_gifts": user_gifts,
        "config": {
            "base_gifts":   config.BASE_GIFTS,
            "main_gifts":   config.MAIN_GIFTS,
            "tg_gifts":     getattr(config, "TG_GIFTS", {}),
            "bot_username": config.BOT_USERNAME,
            "roulette":     config.ROULETTE_CONFIG,
            "cases":        config.CASES_CONFIG,
            "rocket":       config.ROCKET_CONFIG,
            "withdraw_fee": getattr(config, "WITHDRAW_FEE_STARS", 25),
            "donuts_to_stars_rate": getattr(config, "DONUTS_TO_STARS_RATE", 115),
            "gift_exchange_stars_rate": getattr(config, "GIFT_EXCHANGE_STARS_RATE", 0.01),
            "free_case":    getattr(config, "FREE_CASE_CONFIG", None),
        },
    }


@router.post("/topup/stars")
async def create_topup_invoice(data: TopupData, current_user: dict = Depends(get_current_user)):
    """Создаёт платёжную ссылку для Telegram Stars (XTR)."""
    tg_id = current_user["id"]
    payload = f"topup_{tg_id}_{data.stars_amount}"

    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/createInvoiceLink"
    invoice_data = {
        "title":          f"Пополнение на {data.stars_amount} ⭐️",
        "description":    f"Покупка {data.stars_amount} звезд в приложении.",
        "payload":        payload,
        "provider_token": "",
        "currency":       "XTR",
        "prices":         [{"label": f"{data.stars_amount} Stars", "amount": data.stars_amount}],
    }

    async with httpx.AsyncClient() as client:
        resp     = await client.post(url, json=invoice_data)
        res_data = resp.json()

        if res_data.get("ok"):
            return {"status": "ok", "invoice_url": res_data["result"]}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка создания инвойса: {res_data.get('description')}",
            )


@router.get("/history")
async def get_history(
    offset: int = 0,
    limit:  int = 30,
    current_user: dict = Depends(get_current_user),
):
    tg_id   = current_user["id"]
    history = await database.get_user_history(tg_id, limit=limit, offset=offset)
    total   = await database.get_user_history_count(tg_id)
    return {"history": history, "total": total, "offset": offset, "limit": limit}


def _cap_rank(rank) -> str | int:
    """Если место > 100, возвращает строку '99+', иначе — само число."""
    if isinstance(rank, int) and rank > 100:
        return "99+"
    return rank


@router.get("/leaderboard")
async def get_leaderboard(current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]
    board = await database.get_leaderboard()
    user_rank = None
    for i, u in enumerate(board):
        if u["tg_id"] == tg_id:
            user_rank = {"rank": i + 1, "total_gifts": u["total_gifts"]}
            break
    # Пользователь не попал в топ-50 — считаем его реальное место
    if user_rank is None:
        user_rank = await database.get_user_rich_rank(tg_id)
    if user_rank:
        user_rank["rank"] = _cap_rank(user_rank["rank"])
    return {"leaderboard": board, "user_info": user_rank}


@router.get("/leaderboard/rocket")
async def get_rocket_leaderboard(current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]
    full_board = await database.get_rocket_leaderboard_full()
    user_rank = {"rank": "—", "max_multiplier": None}
    for i, u in enumerate(full_board):
        if u["tg_id"] == tg_id:
            user_rank = {"rank": i + 1, "max_multiplier": u["max_multiplier"]}
            break
    user_rank["rank"] = _cap_rank(user_rank["rank"])
    return {"leaderboard": full_board[:50], "user_info": user_rank}


@router.get("/leaderboard/lucky")
async def get_lucky_leaderboard(current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]
    board = await database.get_lucky_leaderboard()
    user_rank = None
    for i, u in enumerate(board):
        if u["tg_id"] == tg_id:
            user_rank = {"rank": i + 1, "ratio": u["ratio"]}
            break
    # Пользователь не попал в топ-50 — считаем его реальное место
    if user_rank is None:
        user_rank = await database.get_user_lucky_rank(tg_id)
    if user_rank:
        user_rank["rank"] = _cap_rank(user_rank["rank"])
    return {"leaderboard": board, "user_info": user_rank}
