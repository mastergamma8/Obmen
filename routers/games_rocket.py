from fastapi import APIRouter, Depends, HTTPException
import random

import config
import database
from models import RocketBetData, RocketCashoutData
from security import verify_user

router = APIRouter(prefix="/rocket", tags=["rocket"])

# ── House Edge для ракеты ─────────────────────────────────────────────────────
HOUSE_EDGE = config.ROCKET_CONFIG.get("house_edge", 0.15)

# Глобальное состояние для активных игр
active_rocket_games = {}


async def generate_crash_point(bet: int) -> float:
    """
    Генерация краш-поинта с учётом Глобального Банка.

    1. Считаем «сырой» краш по формуле (с учётом house_edge).
    2. max_allowed = bank_balance / bet  — ракета не может выплатить
       больше, чем лежит в пуле.
    3. crash_point = min(raw_crash, max_allowed).
    4. Если банк пуст — немедленный краш на 1.00x.
    """
    r = random.uniform(0, 1)
    if r < HOUSE_EDGE:
        raw_crash = 1.00
    else:
        raw_crash = round(0.95 / (1.0 - r), 2)
        max_mult = config.ROCKET_CONFIG.get("max_multiplier", 1000.0)
        raw_crash = min(raw_crash, max_mult)

    bank_balance = await database.bank_get_max_payout()
    if bank_balance <= 0 or bet <= 0:
        return 1.00

    max_allowed = bank_balance / bet
    if max_allowed < 1.00:
        return 1.00

    return min(raw_crash, round(max_allowed, 2))


@router.post("/start")
async def start_rocket(data: RocketBetData, is_valid: bool = Depends(verify_user)):
    user_data = await database.get_user_data(data.tg_id)
    bet = data.bet
    currency = config.ROCKET_CONFIG.get("currency", "donuts")

    if bet < config.ROCKET_CONFIG["min_bet"] or bet > config.ROCKET_CONFIG["max_bet"]:
        raise HTTPException(status_code=400, detail="Неверная сумма ставки")

    user_balance = user_data["stars"] if currency == "stars" else user_data["balance"]
    if user_balance < bet:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно {'звезд' if currency == 'stars' else 'пончиков'}"
        )

    # Списываем ставку с игрока
    if currency == "stars":
        await database.add_stars_to_user(data.tg_id, -bet)
    else:
        await database.add_points_to_user(data.tg_id, -bet)

    # Ставки идут в Глобальный Банк (и звёзды, и пончики)
    bank_info = await database.bank_deposit(bet, HOUSE_EDGE, asset_type=currency)

    crash_point = await generate_crash_point(bet)

    active_rocket_games[data.tg_id] = {
        "bet": bet,
        "currency": currency,
        "crash_point": crash_point,
        "pool_amount": bank_info["pool_amount"] if bank_info else 0,
    }

    updated_user = await database.get_user_data(data.tg_id)
    return {
        "status": "ok",
        "balance": updated_user["balance"],
        "stars": updated_user["stars"],
        "crash_point": crash_point
    }


@router.post("/cashout")
async def cashout_rocket(data: RocketCashoutData, is_valid: bool = Depends(verify_user)):
    if data.tg_id not in active_rocket_games:
        raise HTTPException(status_code=400, detail="Активная игра не найдена или уже завершена")

    game = active_rocket_games.pop(data.tg_id)
    currency = game.get("currency", "donuts")

    if data.multiplier <= game["crash_point"]:
        win_amount = int(game["bet"] * data.multiplier)
        profit = win_amount - game["bet"]

        # Для звёздных игр: прибыль сверх ставки идёт из банка
        if currency == "stars" and profit > 0:
            paid = await database.bank_payout(profit, asset_type=currency)
            if not paid:
                # Банк опустел — форсируем проигрыш
                await database.add_history_entry(
                    data.tg_id, "rocket_lose_stars",
                    "Ракета: банк исчерпан при кешауте", -game["bet"]
                )
                updated_user = await database.get_user_data(data.tg_id)
                return {
                    "status": "error",
                    "detail": "Банк исчерпан. Ракета упала!",
                    "balance": updated_user["balance"],
                    "stars": updated_user["stars"]
                }

        if currency == "stars":
            await database.add_stars_to_user(data.tg_id, win_amount)
        else:
            await database.add_points_to_user(data.tg_id, win_amount)

        await database.add_history_entry(
            data.tg_id, f"rocket_win_{currency}",
            f"Ракета (x{data.multiplier:.2f})", win_amount - game["bet"]
        )

        updated_user = await database.get_user_data(data.tg_id)
        return {
            "status": "ok",
            "win_amount": win_amount,
            "balance": updated_user["balance"],
            "stars": updated_user["stars"]
        }
    else:
        await database.add_history_entry(
            data.tg_id, f"rocket_lose_{currency}",
            "Ракета проигрыш", -game["bet"]
        )
        updated_user = await database.get_user_data(data.tg_id)
        return {
            "status": "error",
            "detail": "Ракета уже улетела!",
            "balance": updated_user["balance"],
            "stars": updated_user["stars"]
        }


@router.post("/crash")
async def crash_rocket(data: RocketBetData, is_valid: bool = Depends(verify_user)):
    """Вызывается фронтендом когда ракета улетела и игрок не успел забрать."""
    game = active_rocket_games.pop(data.tg_id, None)
    if not game:
        return {"status": "ok", "already_closed": True}

    currency = game.get("currency", "donuts")
    # Ставка уже в банке (deposit сделан на старте) — только логируем
    await database.add_history_entry(
        data.tg_id, f"rocket_lose_{currency}",
        f"Ракета улетела на x{game['crash_point']:.2f} (ставка: {game['bet']})", -game["bet"]
    )

    updated_user = await database.get_user_data(data.tg_id)
    return {
        "status": "ok",
        "balance": updated_user["balance"],
        "stars": updated_user["stars"]
    }
