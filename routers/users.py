from fastapi import APIRouter, Depends, HTTPException, Header
import httpx
import json
from urllib.parse import parse_qsl

import config
import database
from handlers.models import TopupData, PromoRedeemData
from handlers.security import get_current_user

router = APIRouter(prefix="/api", tags=["users"])


def _parse_user_id_from_init_data(init_data: str) -> int | None:
    """
    Извлекает user_id из строки Telegram InitData БЕЗ проверки HMAC.
    Используется только для /features и maintenance middleware —
    чтобы определить beta-тестера до полной авторизации.
    Полная HMAC-валидация всегда выполняется в get_current_user().
    """
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        user = json.loads(parsed.get("user", "{}"))
        uid = user.get("id")
        return int(uid) if uid else None
    except Exception:
        return None


@router.post("/init")
async def init_user(current_user: dict = Depends(get_current_user)):
    tg_id      = current_user["id"]
    username   = current_user["username"]
    first_name = current_user["first_name"]
    photo_url  = current_user["photo_url"]

    await database.upsert_user(tg_id, username, first_name, photo_url)
    user_data  = await database.get_user_data(tg_id)
    user_gifts = await database.get_user_gifts(tg_id)
    promo_cases = await database.get_user_promo_cases(tg_id)

    feature_flags    = await database.get_feature_flags()
    maintenance_mode = await database.get_maintenance_mode()

    # Beta-тестеры всегда видят приложение как будто всё включено
    if maintenance_mode or any(not v for v in feature_flags.values()):
        if await database.is_beta_tester(tg_id):
            maintenance_mode = False
            feature_flags = {k: True for k in feature_flags}

    from db.db_settings import get_exchange_bonus_percent
    exchange_bonus_percent = await get_exchange_bonus_percent()

    return {
        "status": "ok",
        "balance": user_data.get("balance", 0),
        "stars":   user_data.get("stars", 0),
        "user_gifts": user_gifts,
        "promo_case_credits": {str(k): v for k, v in promo_cases.items()},
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
            "exchange_bonus_percent": exchange_bonus_percent,
            "free_case":    getattr(config, "FREE_CASE_CONFIG", None),
        },
        "feature_flags":    feature_flags,
        "maintenance_mode": maintenance_mode,
    }



@router.post("/promo/redeem")
async def redeem_promo(data: PromoRedeemData, current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]
    code = (data.code or "").strip().upper()

    if not code:
        raise HTTPException(status_code=400, detail="Введите промокод")

    success, status_key, promo = await database.redeem_promo_code(tg_id, code)
    if not success:
        messages = {
            "promo_not_found": "Промокод не найден",
            "promo_already_used": "Этот промокод уже использован вами",
            "promo_no_uses": "У промокода закончились активации",
        }
        raise HTTPException(status_code=400, detail=messages.get(status_key, "Не удалось активировать промокод"))

    user_data = await database.get_user_data(tg_id)
    promo_cases = await database.get_user_promo_cases(tg_id)

    reward_type = promo["reward_type"]
    reward_value = promo["reward_value"]

    detail = {
        "type": reward_type,
        "value": reward_value,
        "case_id": promo["case_id"],
        "code": promo["code"],
    }

    return {
        "status": "ok",
        "detail": detail,
        "balance": user_data.get("balance", 0),
        "stars": user_data.get("stars", 0),
        "promo_case_credits": {str(k): v for k, v in promo_cases.items()},
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
            user_rank = {
                "rank": i + 1,
                "donuts_spent": u.get("donuts_spent", 0),
                "stars_spent": u.get("stars_spent", 0),
            }
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



@router.get("/features")
async def get_features(x_tg_data: str | None = Header(None)):
    """Публичный эндпоинт — возвращает флаги видимости и режим обслуживания.
    Не требует авторизации, чтобы показывать maintenance-экран до /init.
    Если передан заголовок X-Tg-Data и пользователь является beta-тестером,
    возвращает maintenance_mode=false и все флаги включёнными."""
    maintenance_mode = await database.get_maintenance_mode()
    feature_flags    = await database.get_feature_flags()

    # Beta-тестер: читаем user_id из InitData без полной HMAC-валидации.
    # Это безопасно — мы лишь показываем UI, а полная проверка подписи
    # произойдёт при каждом реальном API-вызове через get_current_user().
    if maintenance_mode or any(not v for v in feature_flags.values()):
        if x_tg_data:
            user_id = _parse_user_id_from_init_data(x_tg_data)
            if user_id and await database.is_beta_tester(user_id):
                maintenance_mode = False
                feature_flags = {k: True for k in feature_flags}

    return {
        "maintenance_mode": maintenance_mode,
        "feature_flags":    feature_flags,
    }