from fastapi import APIRouter, Depends, HTTPException
import httpx

import config
import database
from models import UserInitData, TopupData
from security import verify_user

router = APIRouter(prefix="/api", tags=["users"])

@router.post("/init")
async def init_user(user: UserInitData, is_valid: bool = Depends(verify_user)):
    await database.upsert_user(user.tg_id, user.username, user.first_name, user.photo_url)
    user_data = await database.get_user_data(user.tg_id)
    user_gifts = await database.get_user_gifts(user.tg_id)
    
    return {
        "status": "ok", 
        "balance": user_data.get("balance", 0),
        "stars": user_data.get("stars", 0),
        "user_gifts": user_gifts,
        "config": {
            "base_gifts": config.BASE_GIFTS,
            "main_gifts": config.MAIN_GIFTS,
            "bot_username": config.BOT_USERNAME,
            "roulette": config.ROULETTE_CONFIG,
            "cases": config.CASES_CONFIG,
            "rocket": config.ROCKET_CONFIG,
            "withdraw_fee": getattr(config, "WITHDRAW_FEE_STARS", 25),
            "free_case": getattr(config, "FREE_CASE_CONFIG", None)
        }
    }

@router.post("/topup/stars")
async def create_topup_invoice(data: TopupData, is_valid: bool = Depends(verify_user)):
    """Создает платежную ссылку для Telegram Stars (XTR)"""
    payload = f"topup_{data.tg_id}_{data.stars_amount}"
    
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/createInvoiceLink"
    invoice_data = {
        "title": f"Пополнение на {data.stars_amount} ⭐️",
        "description": f"Покупка {data.stars_amount} звезд в приложении.",
        "payload": payload,
        "provider_token": "", 
        "currency": "XTR",
        "prices": [{"label": f"{data.stars_amount} Stars", "amount": data.stars_amount}]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=invoice_data)
        res_data = resp.json()
        
        if res_data.get("ok"):
            return {"status": "ok", "invoice_url": res_data["result"]}
        else:
            raise HTTPException(status_code=400, detail=f"Ошибка создания инвойса: {res_data.get('description')}")

@router.get("/history")
async def get_history(tg_id: int, offset: int = 0, limit: int = 30, is_valid: bool = Depends(verify_user)):
    history = await database.get_user_history(tg_id, limit=limit, offset=offset)
    total = await database.get_user_history_count(tg_id)
    return {"history": history, "total": total, "offset": offset, "limit": limit}

@router.get("/leaderboard")
async def get_leaderboard(tg_id: int, is_valid: bool = Depends(verify_user)):
    """Богачи: топ по балансу пончиков."""
    board = await database.get_leaderboard()
    user_rank = None
    for i, u in enumerate(board):
        if u["tg_id"] == tg_id:
            user_rank = {"rank": i + 1, "total_gifts": u["total_gifts"]}
            break
    if not user_rank:
        user_rank = {"rank": "99+", "total_gifts": 0}
    return {"leaderboard": board, "user_info": user_rank}

@router.get("/leaderboard/rocket")
async def get_rocket_leaderboard(tg_id: int, is_valid: bool = Depends(verify_user)):
    """Сорвиголовы: топ по максимальному множителю в ракете за неделю."""
    board = await database.get_rocket_leaderboard()
    user_rank = None
    for i, u in enumerate(board):
        if u["tg_id"] == tg_id:
            user_rank = {"rank": i + 1, "max_multiplier": u["max_multiplier"]}
            break
    if not user_rank:
        user_rank = {"rank": "—", "max_multiplier": None}
    return {"leaderboard": board, "user_info": user_rank}

@router.get("/leaderboard/lucky")
async def get_lucky_leaderboard(tg_id: int, is_valid: bool = Depends(verify_user)):
    """Счастливчики: топ по коэффициенту выигрыш/затраты из кейсов."""
    board = await database.get_lucky_leaderboard()
    user_rank = None
    for i, u in enumerate(board):
        if u["tg_id"] == tg_id:
            user_rank = {"rank": i + 1, "ratio": u["ratio"]}
            break
    if not user_rank:
        user_rank = {"rank": "—", "ratio": None}
    return {"leaderboard": board, "user_info": user_rank}