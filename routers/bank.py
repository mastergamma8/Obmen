"""
routers/bank.py — Административный роутер для управления Глобальным Банком.

Топап доступен только администратору (ADMIN_ID из config).
tg_id администратора извлекается из TG InitData через get_current_user.
"""
from fastapi import APIRouter, Depends, HTTPException

import config
import database
from handlers.models import AdminBankTopup
from handlers.security import get_current_user

router = APIRouter(prefix="/bank", tags=["bank"])


def _safe_rtp(paid_out: int, deposited: int) -> float:
    if deposited <= 0:
        return 0.0
    return round(paid_out / deposited * 100, 2)


# ── Публичный статус банка ────────────────────────────────────────────────────

@router.get("/status")
async def bank_status():
    bank = await database.get_bank()
    rate = config.DONUTS_TO_STARS_RATE

    stars_bal  = bank.get("stars_balance", 0)
    donuts_bal = bank.get("donuts_balance", 0)
    gift_bal   = bank.get("gift_value_balance", 0)
    total_liq  = stars_bal + donuts_bal * rate + gift_bal  # FIX: с курсом

    total_dep   = bank.get("total_deposited_value", 0)
    total_paid  = bank.get("total_paid_out_value", 0)
    total_edge  = bank.get("total_house_edge_value", 0)

    stars_dep   = bank.get("stars_deposited", 0)
    stars_paid  = bank.get("stars_paid_out", 0)
    donuts_dep  = bank.get("donuts_deposited", 0)
    donuts_paid = bank.get("donuts_paid_out", 0)
    gift_paid   = bank.get("gift_value_paid_out", 0)

    return {
        "exchange_rate": {
            "donuts_to_stars": rate,
            "note": f"1 donut = {rate} stars (bank value)",
        },
        "liquidity": {
            "stars":           stars_bal,
            "donuts":          donuts_bal,
            "donuts_in_stars": donuts_bal * rate,
            "gift_value":      gift_bal,
            "total_in_stars":  total_liq,
        },
        "total": {
            "deposited":   total_dep,
            "paid_out":    total_paid,
            "house_edge":  total_edge,
            "rtp_percent": _safe_rtp(total_paid, total_dep),
        },
        "stars": {
            "deposited":   stars_dep,
            "paid_out":    stars_paid,
            "rtp_percent": _safe_rtp(stars_paid, stars_dep),
        },
        "donuts": {
            "deposited":   donuts_dep,
            "paid_out":    donuts_paid,
            "rtp_percent": _safe_rtp(donuts_paid, donuts_dep),
        },
        "gifts": {
            "value_paid_out": gift_paid,
        },
    }


# ── Администраторский топап ───────────────────────────────────────────────────

@router.post("/topup")
async def bank_topup(data: AdminBankTopup, current_user: dict = Depends(get_current_user)):
    """
    Пополнение банка администратором.
    Проверка прав — по серверному current_user["id"], не по данным из тела.
    """
    if current_user["id"] != config.ADMIN_ID:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть > 0")
    if data.asset_type not in ("stars", "donuts"):
        raise HTTPException(status_code=400, detail="asset_type должен быть 'stars' или 'donuts'")

    if data.asset_type == "donuts":
        await database.bank_add_donuts(data.amount)
    else:
        await database.bank_add_stars(data.amount)

    bank  = await database.get_bank()
    rate  = config.DONUTS_TO_STARS_RATE
    total_liq = (
        bank.get("stars_balance", 0)
        + bank.get("donuts_balance", 0) * rate
        + bank.get("gift_value_balance", 0)
    )
    return {
        "status":             "ok",
        "asset_type":         data.asset_type,
        "added":              data.amount,
        "new_stars_balance":  bank.get("stars_balance", 0),
        "new_donuts_balance": bank.get("donuts_balance", 0),
        "total_liquidity":    total_liq,
    }
