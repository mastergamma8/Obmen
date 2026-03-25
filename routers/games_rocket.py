from fastapi import APIRouter, Depends, HTTPException
import random

import config
import database
from models import RocketBetData, RocketCashoutData
from security import verify_user

router = APIRouter(prefix="/rocket", tags=["rocket"])

# Глобальное состояние для активных игр в ракету
active_rocket_games = {}


def generate_crash_point() -> float:
    """Генерация коэффициента краша на основе конфига."""
    r = random.uniform(0, 1)
    if r < config.ROCKET_CONFIG["house_edge"]:
        return 1.00
    crash_point = round(0.95 / (1.0 - r), 2)
    max_mult = config.ROCKET_CONFIG["max_multiplier"]
    return min(crash_point, max_mult)


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

    if currency == "stars":
        await database.add_stars_to_user(data.tg_id, -bet)
    else:
        await database.add_points_to_user(data.tg_id, -bet)

    crash_point = generate_crash_point()

    active_rocket_games[data.tg_id] = {
        "bet": bet,
        "currency": currency,
        "crash_point": crash_point
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
        # Игра уже закрыта (например, игрок успел сделать cashout в последний момент)
        return {"status": "ok", "already_closed": True}

    currency = game.get("currency", "donuts")

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
