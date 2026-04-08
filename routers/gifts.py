from fastapi import APIRouter, Depends, HTTPException
import httpx
import time

import cloudscraper
import config
import database
from handlers.models import ActionData
from handlers.security import get_current_user
from handlers.tg_gifts import get_gift_def, is_real_tg_gift, send_real_tg_gift, get_tg_exchange_value

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
    await database.log_action(tg_id, "claim_gift", f"Покупка подарка: {gift_name} [gift_id:{data.gift_id}]", -cost)

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

    gift_def = get_gift_def(data.gift_id)
    if not gift_def:
        raise HTTPException(status_code=400, detail="Неверный ID подарка")

    user_gifts = await database.get_user_gifts(tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")

    gift_name = gift_def.get("name", "Неизвестный подарок")

    # Реальные Telegram-подарки выводятся без комиссии и без кулдауна
    if is_real_tg_gift(data.gift_id):
        removed = await database.remove_gift_from_user(tg_id, data.gift_id)
        if not removed:
            raise HTTPException(status_code=400, detail="Подарок не найден")

        sent = await send_real_tg_gift(
            tg_id,
            gift_def["tg_gift_id"],
            text=f"gift from Space Donut 🍩"
        )
        if not sent:
            await database.add_gift_to_user(tg_id, data.gift_id, 1)
            raise HTTPException(status_code=502, detail="Не удалось отправить Telegram-подарок")

        await database.add_history_entry(
            tg_id,
            "withdraw_tg_gift",
            f"Вывод Telegram подарка: {gift_name} [gift_id:{data.gift_id}]",
            0
        )

        updated_gifts = await database.get_user_gifts(tg_id)
        updated_user  = await database.get_user_data(tg_id)
        return {
            "status": "ok",
            "user_gifts": updated_gifts,
            "balance": updated_user.get("balance", 0),
            "stars": updated_user.get("stars", 0),
        }

    # Старый вывод для обычных подарков — с комиссией и кулдауном
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

    # Атомарное списание комиссии
    success_deduct = await database.deduct_stars(tg_id, config.WITHDRAW_FEE_STARS)
    if not success_deduct:
        raise HTTPException(status_code=400, detail="not_enough_stars")

    # Атомарное списание подарка — проверяем результат
    removed = await database.remove_gift_from_user(tg_id, data.gift_id)
    if not removed:
        await database.add_stars_to_user(tg_id, config.WITHDRAW_FEE_STARS)
        raise HTTPException(status_code=400, detail="Подарок не найден")

    await database.update_last_gift_withdraw(tg_id, now)

    await database.log_action(tg_id, "withdraw_gift", f"Вывод подарка: {gift_name} [gift_id:{data.gift_id}]", 0)

    # Уведомление админа
    try:
        user_profile = await database.get_user_profile(tg_id)
        username_str = f"@{user_profile['username']}" if user_profile.get("username") else "Отсутствует/Скрыт"
        first_name   = user_profile.get("first_name", "Без имени")
        admin_text = (
            f"🚨 <b>Новая заявка на вывод подарка!</b>\n\n"
            f"👤 Пользователь: <a href='tg://user?id={tg_id}'>{first_name}</a>\n"
            f"🔗 Юзернейм: {username_str}\n"
            f"🆔 ID: <code>{tg_id}</code>\n\n"
            f"🎁 <b>Подарок:</b> {gift_name} [gift_id:{data.gift_id}] (ID: {data.gift_id})"
        )
        url     = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {"chat_id": config.ADMIN_ID, "text": admin_text, "parse_mode": "HTML"}
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка при отправке уведомления админу: {e}")

    updated_gifts = await database.get_user_gifts(tg_id)

    return {"status": "ok", "user_gifts": updated_gifts}


@router.post("/exchange")
async def exchange_gift(data: ActionData, current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]

    gift_def = get_gift_def(data.gift_id)
    if not gift_def or not is_real_tg_gift(data.gift_id):
        raise HTTPException(status_code=400, detail="Можно обменивать только реальные Telegram-подарки")

    user_gifts = await database.get_user_gifts(tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")

    reward_stars = get_tg_exchange_value(data.gift_id)
    if reward_stars <= 0:
        raise HTTPException(status_code=400, detail="Неверная цена обмена")

    removed = await database.remove_gift_from_user(tg_id, data.gift_id)
    if not removed:
        raise HTTPException(status_code=400, detail="Подарок не найден")

    await database.add_stars_to_user(tg_id, reward_stars)
    await database.log_action(
        tg_id,
        "exchange_tg_gift",
        f"Обмен Telegram подарка: {gift_def['name']} [gift_id:{data.gift_id}] -> +{reward_stars} ⭐",
        reward_stars,
    )

    updated_user  = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)
    return {
        "status": "ok",
        "balance": updated_user.get("balance", 0),
        "stars": updated_user.get("stars", 0),
        "user_gifts": updated_gifts,
        "exchange_stars": reward_stars,
    }

def _fetch_portal_floor_price(gift_name: str) -> float | None:
    """Синхронно запрашивает floor_price подарка у Portal Market API."""
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        resp = scraper.get(
            "https://portal-market.com/api/collections",
            params={"search": gift_name, "limit": 1},
            timeout=8,
        )
        if resp.status_code == 200:
            collections = resp.json().get("collections", [])
            if collections:
                fp = float(collections[0].get("floor_price", 0))
                return fp if fp > 0 else None
    except Exception as e:
        print(f"[exchange-for-donuts] Portal API error for '{gift_name}': {e}")
    return None


@router.post("/exchange-for-donuts")
async def exchange_for_donuts(data: ActionData, current_user: dict = Depends(get_current_user)):
    """Устаревший эндпоинт. Перенаправляет на /api/exchange-for-stars."""
    raise HTTPException(
        status_code=410,
        detail="Этот эндпоинт устарел. Используйте /api/exchange-for-stars",
    )


@router.post("/exchange-for-stars")
async def exchange_for_stars(data: ActionData, current_user: dict = Depends(get_current_user)):
    """
    Обменять BASE_GIFT или MAIN_GIFT подарок на звёзды.

    Для BASE_GIFTS цена берётся с Portal Market API (-20%), затем конвертируется
    из пончиков в звёзды по курсу config.DONUTS_TO_STARS_RATE (звёзд за 1 пончик).

    Для MAIN_GIFTS в качестве базы используется required_value подарка,
    аналогично конвертируется в звёзды.

    TG-подарки для этого эндпоинта не принимаются — используйте /api/exchange.
    """
    tg_id = current_user["id"]

    # Определяем тип подарка: BASE или MAIN
    gift_def = config.BASE_GIFTS.get(data.gift_id)
    gift_type = "base"
    if not gift_def:
        gift_def = config.MAIN_GIFTS.get(data.gift_id)
        gift_type = "main"

    if not gift_def:
        raise HTTPException(status_code=400, detail="Только базовые и основные подарки можно обменять на звёзды")

    # TG-подарки через этот эндпоинт не обслуживаем
    from handlers.tg_gifts import is_real_tg_gift as _is_real_tg
    if _is_real_tg(data.gift_id):
        raise HTTPException(status_code=400, detail="Используйте /api/exchange для Telegram-подарков")

    # Проверяем наличие подарка в инвентаре
    user_gifts = await database.get_user_gifts(tg_id)
    if user_gifts.get(data.gift_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="У вас нет этого подарка")

    gift_name = gift_def["name"]

    # Получаем базовую стоимость в пончиках
    if gift_type == "base":
        # Актуальная цена с Portal API (-20%)
        floor_price = _fetch_portal_floor_price(gift_name)
        if floor_price is None or floor_price <= 0:
            fallback = int(gift_def.get("value", 0))
            if fallback <= 0:
                raise HTTPException(status_code=503, detail="Не удалось получить актуальную цену подарка")
            floor_price = fallback / 0.8  # обратный пересчёт до скидки
        donuts_value = int(floor_price * 0.8)
    else:
        # MAIN_GIFT: берём required_value напрямую
        donuts_value = int(gift_def.get("required_value", gift_def.get("value", 0)))

    if donuts_value <= 0:
        raise HTTPException(status_code=400, detail="Цена подарка слишком мала для обмена")

    # Конвертируем пончики -> звёзды
    # DONUTS_TO_STARS_RATE — количество звёзд за 1 пончик
    stars_reward = max(1, int(donuts_value * config.DONUTS_TO_STARS_RATE))

    # Атомарно снимаем подарок
    removed = await database.remove_gift_from_user(tg_id, data.gift_id)
    if not removed:
        raise HTTPException(status_code=400, detail="Подарок не найден")

    # Зачисляем звёзды
    await database.add_stars_to_user(tg_id, stars_reward)

    await database.log_action(
        tg_id,
        "exchange_gift_stars",
        f"Обмен подарка на звёзды: {gift_name} [gift_id:{data.gift_id}] -> +{stars_reward} ⭐",
        stars_reward,
    )

    updated_user  = await database.get_user_data(tg_id)
    updated_gifts = await database.get_user_gifts(tg_id)
    return {
        "status": "ok",
        "stars_reward": stars_reward,
        "balance": updated_user.get("balance", 0),
        "stars": updated_user.get("stars", 0),
        "user_gifts": updated_gifts,
    }
