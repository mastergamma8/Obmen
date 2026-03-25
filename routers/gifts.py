from fastapi import APIRouter, Depends, HTTPException
import httpx
import time

import config
import database
from models import ActionData
from security import verify_user

router = APIRouter(prefix="/api", tags=["gifts"])

GIFT_COOLDOWN_SECONDS = 5 * 3600  # 5 часов


@router.post("/claim")
async def claim_gift(data: ActionData, is_valid: bool = Depends(verify_user)):
    if data.gift_id not in config.MAIN_GIFTS:
        raise HTTPException(status_code=400, detail="Неверный ID подарка")

    now = int(time.time())

    # ПРОВЕРКА ТАЙМЕРА ДЛЯ ПОКУПКИ (Главная)
    last_claim = await database.get_last_gift_claim(data.tg_id)
    elapsed = now - last_claim
    if elapsed < GIFT_COOLDOWN_SECONDS:
        seconds_left = GIFT_COOLDOWN_SECONDS - elapsed
        hours_left = seconds_left // 3600
        minutes_left = (seconds_left % 3600) // 60
        raise HTTPException(
            status_code=429,
            detail={"error": "cooldown", "type": "claim", "hours": hours_left, "minutes": minutes_left}
        )

    cost = config.MAIN_GIFTS[data.gift_id]["required_value"]
    success = await database.claim_main_gift(data.tg_id, data.gift_id, cost)

    if not success:
        raise HTTPException(status_code=400, detail="Недостаточно поинтов")

    # Обновляем время ПОКУПКИ
    await database.update_last_gift_claim(data.tg_id, now)

    gift_name_for_history = config.MAIN_GIFTS[data.gift_id]["name"]
    await database.log_action(
        data.tg_id, "claim_gift", f"Покупка подарка: {gift_name_for_history}", -cost
    )

    # Начисляем рефку
    gift_value = config.MAIN_GIFTS[data.gift_id].get("value", cost)
    await database.distribute_referral_bonus(data.tg_id, gift_value)

    user_data = await database.get_user_data(data.tg_id)
    updated_gifts = await database.get_user_gifts(data.tg_id)

    return {
        "status": "ok",
        "balance": user_data.get("balance", 0),
        "user_gifts": updated_gifts
    }


@router.post("/withdraw")
async def withdraw_gift(data: ActionData, is_valid: bool = Depends(verify_user)):
    now = int(time.time())

    # ПРОВЕРКА ТАЙМЕРА ДЛЯ ВЫВОДА (Инвентарь)
    last_withdraw = await database.get_last_gift_withdraw(data.tg_id)
    elapsed = now - last_withdraw
    if elapsed < GIFT_COOLDOWN_SECONDS:
        seconds_left = GIFT_COOLDOWN_SECONDS - elapsed
        hours_left = seconds_left // 3600
        minutes_left = (seconds_left % 3600) // 60
        raise HTTPException(
            status_code=429,
            detail={"error": "cooldown", "type": "withdraw", "hours": hours_left, "minutes": minutes_left}
        )

    # get_user_gifts возвращает dict с int-ключами — сравниваем int с int
    user_gifts = await database.get_user_gifts(data.tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")

    gift_name_for_history = "Неизвестный подарок"
    if data.gift_id in config.MAIN_GIFTS:
        gift_name_for_history = config.MAIN_GIFTS[data.gift_id]["name"]
    elif data.gift_id in config.BASE_GIFTS:
        gift_name_for_history = config.BASE_GIFTS[data.gift_id]["name"]

    # Списываем подарок и обновляем таймер ВЫВОДА
    # 1. Проверяем, достаточно ли звезд
    user_data = await database.get_user_data(data.tg_id)
    if user_data.get("stars", 0) < config.WITHDRAW_FEE_STARS:
        raise HTTPException(status_code=400, detail="not_enough_stars")
        
    # 2. Пытаемся списать комиссию
    success_deduct = await database.deduct_stars(data.tg_id, config.WITHDRAW_FEE_STARS)
    if not success_deduct:
        raise HTTPException(status_code=400, detail="not_enough_stars")

    await database.remove_gift_from_user(data.tg_id, data.gift_id)
    await database.update_last_gift_withdraw(data.tg_id, now)

    await database.log_action(
        data.tg_id, "withdraw_gift", f"Вывод подарка: {gift_name_for_history}", 0
    )

    updated_gifts = await database.get_user_gifts(data.tg_id)

    # Уведомляем админа
    try:
        user_profile = await database.get_user_profile(data.tg_id)
        username_str = f"@{user_profile['username']}" if user_profile.get("username") else "Отсутствует/Скрыт"
        first_name = user_profile.get("first_name", "Без имени")

        admin_text = (
            f"🚨 <b>Новая заявка на вывод подарка!</b>\n\n"
            f"👤 Пользователь: <a href='tg://user?id={data.tg_id}'>{first_name}</a>\n"
            f"🔗 Юзернейм: {username_str}\n"
            f"🆔 ID: <code>{data.tg_id}</code>\n\n"
            f"🎁 <b>Подарок:</b> {gift_name_for_history} (ID: {data.gift_id})"
        )

        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.ADMIN_ID,
            "text": admin_text,
            "parse_mode": "HTML"
        }
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка при отправке уведомления админу: {e}")

    return {"status": "ok", "user_gifts": updated_gifts}