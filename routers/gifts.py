from fastapi import APIRouter, Depends, HTTPException
import httpx
import time

import config
import database
from handlers.models import ActionData
from handlers.security import get_current_user

router = APIRouter(prefix="/api", tags=["gifts"])

GIFT_COOLDOWN_SECONDS = 5 * 3600  # 5 часов


@router.post("/claim")
async def claim_gift(data: ActionData, current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]

    if data.gift_id not in config.MAIN_GIFTS:
        raise HTTPException(status_code=400, detail="Неверный ID подарка")

    now = int(time.time())

    last_claim = await database.get_last_gift_claim(tg_id)
    elapsed    = now - last_claim
    if elapsed < GIFT_COOLDOWN_SECONDS:
        seconds_left = GIFT_COOLDOWN_SECONDS - elapsed
        raise HTTPException(
            status_code=429,
            detail={
                "error":   "cooldown",
                "type":    "claim",
                "hours":   seconds_left // 3600,
                "minutes": (seconds_left % 3600) // 60,
            },
        )

    cost    = config.MAIN_GIFTS[data.gift_id]["required_value"]
    success = await database.claim_main_gift(tg_id, data.gift_id, cost)

    if not success:
        raise HTTPException(status_code=400, detail="Недостаточно поинтов")

    await database.update_last_gift_claim(tg_id, now)

    gift_name = config.MAIN_GIFTS[data.gift_id]["name"]
    await database.log_action(tg_id, "claim_gift", f"Покупка подарка: {gift_name}", -cost)

    gift_value = config.MAIN_GIFTS[data.gift_id].get("value", cost)
    await database.distribute_referral_bonus(tg_id, gift_value)

    user_data    = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)

    return {
        "status":     "ok",
        "balance":    user_data.get("balance", 0),
        "user_gifts": updated_gifts,
    }


@router.post("/withdraw")
async def withdraw_gift(data: ActionData, current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]
    now   = int(time.time())

    last_withdraw = await database.get_last_gift_withdraw(tg_id)
    elapsed       = now - last_withdraw
    if elapsed < GIFT_COOLDOWN_SECONDS:
        seconds_left = GIFT_COOLDOWN_SECONDS - elapsed
        raise HTTPException(
            status_code=429,
            detail={
                "error":   "cooldown",
                "type":    "withdraw",
                "hours":   seconds_left // 3600,
                "minutes": (seconds_left % 3600) // 60,
            },
        )

    user_gifts = await database.get_user_gifts(tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")

    # Атомарное списание комиссии
    success_deduct = await database.deduct_stars(tg_id, config.WITHDRAW_FEE_STARS)
    if not success_deduct:
        raise HTTPException(status_code=400, detail="not_enough_stars")

    # Атомарное списание подарка — проверяем результат (пункт 4)
    removed = await database.remove_gift_from_user(tg_id, data.gift_id)
    if not removed:
        # Возвращаем звёзды, если подарок не найден
        await database.add_stars_to_user(tg_id, config.WITHDRAW_FEE_STARS)
        raise HTTPException(status_code=400, detail="Подарок не найден")

    await database.update_last_gift_withdraw(tg_id, now)

    gift_name = "Неизвестный подарок"
    if data.gift_id in config.MAIN_GIFTS:
        gift_name = config.MAIN_GIFTS[data.gift_id]["name"]
    elif data.gift_id in config.BASE_GIFTS:
        gift_name = config.BASE_GIFTS[data.gift_id]["name"]

    await database.log_action(tg_id, "withdraw_gift", f"Вывод подарка: {gift_name}", 0)

    updated_gifts = await database.get_user_gifts(tg_id)

    # Уведомление админа
    try:
        user_profile  = await database.get_user_profile(tg_id)
        username_str  = f"@{user_profile['username']}" if user_profile.get("username") else "Отсутствует/Скрыт"
        first_name    = user_profile.get("first_name", "Без имени")
        admin_text = (
            f"🚨 <b>Новая заявка на вывод подарка!</b>\n\n"
            f"👤 Пользователь: <a href='tg://user?id={tg_id}'>{first_name}</a>\n"
            f"🔗 Юзернейм: {username_str}\n"
            f"🆔 ID: <code>{tg_id}</code>\n\n"
            f"🎁 <b>Подарок:</b> {gift_name} (ID: {data.gift_id})"
        )
        url     = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {"chat_id": config.ADMIN_ID, "text": admin_text, "parse_mode": "HTML"}
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка при отправке уведомления админу: {e}")

    return {"status": "ok", "user_gifts": updated_gifts}
