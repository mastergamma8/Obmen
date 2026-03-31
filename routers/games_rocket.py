from fastapi import APIRouter, Depends, HTTPException
import random
import time

import config
import database
from handlers.models import RocketBetData, RocketCashoutData
from handlers.security import get_current_user

router = APIRouter(prefix="/rocket", tags=["rocket"])

HOUSE_EDGE = config.ROCKET_CONFIG.get("house_edge", 0.15)


async def generate_crash_point(bet: int) -> float:
    """
    Генерация краш-поинта с учётом Глобального Банка.
    Crash-point хранится только на сервере и никогда не передаётся клиенту.
    """
    r = random.uniform(0, 1)
    if r < HOUSE_EDGE:
        raw_crash = 1.00
    else:
        raw_crash = round(0.95 / (1.0 - r), 2)
        max_mult  = config.ROCKET_CONFIG.get("max_multiplier", 1000.0)
        raw_crash = min(raw_crash, max_mult)

    bank_balance = await database.bank_get_max_payout()
    if bank_balance <= 0 or bet <= 0:
        return 1.00

    max_allowed = bank_balance / bet
    if max_allowed < 1.00:
        return 1.00

    return min(raw_crash, round(max_allowed, 2))


@router.post("/start")
async def start_rocket(data: RocketBetData, current_user: dict = Depends(get_current_user)):
    tg_id    = current_user["id"]
    bet      = data.bet
    currency = config.ROCKET_CONFIG.get("currency", "donuts")

    if bet < config.ROCKET_CONFIG["min_bet"] or bet > config.ROCKET_CONFIG["max_bet"]:
        raise HTTPException(status_code=400, detail="Неверная сумма ставки")

    existing = await database.rocket_get_game(tg_id)
    if existing:
        raise HTTPException(status_code=400, detail="У вас уже есть активная игра")

    crash_point = await generate_crash_point(bet)

    result = await database.rocket_start_atomic(
        user_id=tg_id,
        bet=bet,
        currency=currency,
        crash_point=crash_point,
        house_edge=HOUSE_EDGE,
    )

    if not result["ok"]:
        reason = result.get("reason", "")
        if reason == "insufficient_balance":
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'}",
            )
        raise HTTPException(status_code=400, detail="Не удалось создать игру")

    updated_user = await database.get_user_data(tg_id)
    return {
        "status":  "ok",
        "balance": updated_user["balance"],
        "stars":   updated_user["stars"],
        # crash_point намеренно отсутствует в ответе
    }


@router.post("/cashout")
async def cashout_rocket(data: RocketCashoutData, current_user: dict = Depends(get_current_user)):
    """
    Кешаут по команде игрока.

    Клиент передаёт multiplier — тот множитель, на котором сработал авто-вывод
    или игрок нажал «Забрать». Сервер независимо рассчитывает серверный множитель
    по прошедшему времени и берёт минимум из двух значений.

    Это решает проблему с историей: при авто-выводе на 1.50 сетевая задержка
    (50–200 мс) раньше приводила к тому, что сервер записывал 1.74 или 1.79,
    потому что считал время уже после получения запроса. Теперь клиентское
    значение используется как верхняя граница, а сервер не может занизить его
    ниже 1.0 или дать больше, чем успело нарасти реально.
    """
    tg_id = current_user["id"]

    game = await database.rocket_end_game(tg_id)
    if not game:
        raise HTTPException(status_code=400, detail="Активная игра не найдена или уже завершена")

    currency    = game.get("currency", "donuts")
    bet         = game["bet"]
    crash_point = game["crash_point"]
    created_at  = game.get("created_at", int(time.time()))

    # Серверный расчёт множителя по прошедшему времени
    elapsed     = time.time() - created_at
    growth_rate = config.ROCKET_CONFIG.get("growth_rate", 0.1)
    server_mult = round(1.0 + elapsed * growth_rate, 2)

    # Проверяем краш по серверному времени — это нельзя обойти со стороны клиента
    crashed = server_mult >= crash_point

    if crashed:
        await database.add_history_entry(
            tg_id, f"rocket_lose_{currency}",
            "Ракета проигрыш", -bet
        )
        updated_user = await database.get_user_data(tg_id)
        return {
            "status":  "error",
            "detail":  "Ракета уже улетела!",
            "balance": updated_user["balance"],
            "stars":   updated_user["stars"],
        }

    # Берём минимум из клиентского и серверного значений:
    # — клиент не может передать больше, чем реально выросло на сервере
    # — клиент не может передать меньше 1.0
    # Это гарантирует честную запись в историю без влияния сетевой задержки.
    client_mult = max(1.0, round(float(data.multiplier), 2))
    actual_mult = min(client_mult, server_mult, crash_point)

    win_amount = int(bet * actual_mult)
    profit     = win_amount - bet

    # Прибыль сверх ставки идёт из банка
    if profit > 0:
        paid = await database.bank_payout(profit, asset_type=currency)
        if not paid:
            await database.add_history_entry(
                tg_id, f"rocket_lose_{currency}",
                "Ракета: банк исчерпан при кешауте", -bet
            )
            updated_user = await database.get_user_data(tg_id)
            return {
                "status": "error",
                "detail": "Банк исчерпан. Ракета упала!",
                "balance": updated_user["balance"],
                "stars":   updated_user["stars"],
            }

    if currency == "stars":
        await database.add_stars_to_user(tg_id, win_amount)
    else:
        await database.add_points_to_user(tg_id, win_amount)

    await database.add_history_entry(
        tg_id, f"rocket_win_{currency}",
        f"Ракета (x{actual_mult:.2f})", profit
    )

    updated_user = await database.get_user_data(tg_id)
    return {
        "status":     "ok",
        "win_amount": win_amount,
        "multiplier": actual_mult,
        "balance":    updated_user["balance"],
        "stars":      updated_user["stars"],
    }


@router.post("/crash")
async def crash_rocket(current_user: dict = Depends(get_current_user)):
    """Вызывается фронтендом, когда ракета улетела и игрок не успел кешаутиться."""
    tg_id = current_user["id"]
    game  = await database.rocket_end_game(tg_id)
    if not game:
        return {"status": "ok", "already_closed": True}

    currency = game.get("currency", "donuts")
    await database.add_history_entry(
        tg_id, f"rocket_lose_{currency}",
        f"Ракета улетела на x{game['crash_point']:.2f} (ставка: {game['bet']})", -game["bet"]
    )

    updated_user = await database.get_user_data(tg_id)
    return {
        "status":  "ok",
        "balance": updated_user["balance"],
        "stars":   updated_user["stars"],
    }


@router.get("/status")
async def rocket_status(current_user: dict = Depends(get_current_user)):
    """Возвращает состояние активной игры без раскрытия crash_point."""
    tg_id = current_user["id"]
    game  = await database.rocket_get_game(tg_id)

    if not game:
        return {"status": "no_game"}

    elapsed      = time.time() - game.get("created_at", time.time())
    growth_rate  = config.ROCKET_CONFIG.get("growth_rate", 0.1)
    current_mult = round(1.0 + elapsed * growth_rate, 2)
    crashed      = current_mult >= game["crash_point"]

    return {
        "status":       "active",
        "bet":          game["bet"],
        "currency":     game["currency"],
        "current_mult": current_mult,
        "crashed":      crashed,
    }
