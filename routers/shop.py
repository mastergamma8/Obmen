"""
routers/shop.py
Магазин: конфиг разделов и покупка товаров.

GET  /api/shop/config        — публичный конфиг разделов + лимитированные подарки
GET  /api/shop/referrals     — сколько рефералов доступно для использования в акциях
POST /api/shop/buy           — покупка товара из кастомного раздела
"""

import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import config
import database
from db import db_async as aiosqlite
from db.db_core import DB_NAME
from handlers.security import get_current_user
from handlers.tg_gifts import send_real_tg_gift

router = APIRouter(prefix="/api/shop", tags=["shop"])


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

TG_SHOP_GIFT_IDS: set[int] = {2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019}


def _build_limited_section() -> dict:
    """Строит раздел «Лимитированные подарки» из TG_GIFTS."""
    items = []
    for gift_id in sorted(TG_SHOP_GIFT_IDS):
        gift = config.TG_GIFTS.get(gift_id)
        if not gift or not gift.get("price"):
            continue
        items.append({
            "id":       f"limited_{gift_id}",
            "type":     "limited_gift",
            "gift_id":  gift_id,
            "image":    gift.get("photo", ""),
            "currency": "stars",
            "price":    gift.get("price", 60),
            "title":    {
                "ru": gift.get("name") or f"Подарок #{gift_id}",
                "en": gift.get("name") or f"Gift #{gift_id}",
            },
            "enabled":  True,
        })
    return {
        "id":    "limited_gifts",
        "title": {"ru": "Лимитированные подарки", "en": "Limited Gifts"},
        "items": items,
    }


def _enabled_sections() -> list[dict]:
    """Возвращает только включённые разделы и товары."""
    sections = []
    for section in getattr(config, "SHOP_SECTIONS", []):
        enabled_items = [i for i in section.get("items", []) if i.get("enabled", True)]
        if enabled_items:
            sections.append({**section, "items": enabled_items})
    return sections


async def _get_used_referrals(user_id: int) -> int:
    """Возвращает количество рефералов, уже использованных в акциях."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM shop_referral_purchases WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def _record_referral_purchase(user_id: int, item_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO shop_referral_purchases (user_id, item_id, purchased_at) VALUES (?,?,?)",
            (user_id, item_id, int(time.time()))
        )
        await db.commit()


# ────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────

@router.get("/config")
async def get_shop_config():
    """Возвращает конфиг магазина: лимитированные подарки + кастомные разделы."""
    return {
        "limited_section": _build_limited_section(),
        "sections":        _enabled_sections(),
    }


@router.get("/referrals")
async def get_available_referrals(current_user: dict = Depends(get_current_user)):
    """Возвращает количество рефералов, доступных для использования в акциях."""
    tg_id = current_user["id"]
    from db.db_referrals import get_referrals
    total = len(await get_referrals(tg_id))
    used  = await _get_used_referrals(tg_id)
    return {"total": total, "used": used, "available": max(0, total - used)}


class ShopBuyData(BaseModel):
    item_id:    str
    section_id: str


@router.post("/buy")
async def shop_buy(data: ShopBuyData, current_user: dict = Depends(get_current_user)):
    tg_id = current_user["id"]

    # ── Найти товар в конфиге ───────────────────────────────
    item = None
    for section in _enabled_sections():
        if section["id"] == data.section_id:
            for i in section["items"]:
                if i["id"] == data.item_id:
                    item = i
                    break
        if item:
            break

    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")

    item_type = item["type"]
    currency  = item["currency"]
    price     = item["price"]

    # ── Проверка и списание валюты ──────────────────────────

    if currency == "donuts":
        success = await database.deduct_balance(tg_id, price)
        if not success:
            raise HTTPException(status_code=400, detail="not_enough_donuts")

    elif currency == "stars":
        success = await database.deduct_stars(tg_id, price)
        if not success:
            raise HTTPException(status_code=400, detail="not_enough_stars")

    elif currency == "referral":
        from db.db_referrals import get_referrals
        total     = len(await get_referrals(tg_id))
        used      = await _get_used_referrals(tg_id)
        available = max(0, total - used)
        if available < price:
            raise HTTPException(status_code=400, detail="not_enough_referrals")
        # Записываем использованные рефералы
        for _ in range(price):
            await _record_referral_purchase(tg_id, data.item_id)

    elif currency == "free":
        pass  # бесплатно

    else:
        raise HTTPException(status_code=400, detail="unknown_currency")

    # ── Начисление товара ────────────────────────────────────

    user_data = await database.get_user_data(tg_id)

    if item_type == "stars":
        amount = item["amount"]
        await database.add_stars_to_user(tg_id, amount)
        await database.log_action(
            tg_id, "shop_buy_stars",
            f"Куплено {amount} ⭐ в магазине [{data.item_id}]", amount
        )

    elif item_type == "donuts":
        amount = item["amount"]
        await database.add_points_to_user(tg_id, amount)
        await database.log_action(
            tg_id, "shop_buy_donuts",
            f"Куплено {amount} 🍩 в магазине [{data.item_id}]", amount
        )

    elif item_type in ("limited_gift", "base_gift"):
        gift_id  = item.get("gift_id")

        if item_type == "limited_gift":
            # Лимитированный подарок — отправляется через Telegram Gift API
            gift_def   = config.TG_GIFTS.get(gift_id)
            if not gift_def:
                if currency == "donuts": await database.add_points_to_user(tg_id, price)
                elif currency == "stars": await database.add_stars_to_user(tg_id, price)
                raise HTTPException(status_code=400, detail="gift_config_not_found")

            tg_gift_id = gift_def.get("tg_gift_id")
            sent = await send_real_tg_gift(tg_id, tg_gift_id, text="gift from Space Donut 🍩")
            if not sent:
                if currency == "donuts": await database.add_points_to_user(tg_id, price)
                elif currency == "stars": await database.add_stars_to_user(tg_id, price)
                raise HTTPException(status_code=502, detail="send_gift_failed")

            gift_name = gift_def.get("name") or f"Gift #{gift_id}"
            await database.log_action(
                tg_id, "shop_buy_gift",
                f"Куплен лимит. подарок '{gift_name}' в магазине [{data.item_id}]", -price
            )

        else:
            # Base gift — добавляется в профиль пользователя (BASE_GIFTS, ID 1–114)
            gift_def = config.BASE_GIFTS.get(gift_id)
            if not gift_def:
                if currency == "donuts": await database.add_points_to_user(tg_id, price)
                elif currency == "stars": await database.add_stars_to_user(tg_id, price)
                raise HTTPException(status_code=400, detail="gift_config_not_found")

            await database.add_gift_to_user(tg_id, gift_id, 1)
            gift_name = gift_def.get("name") or f"Gift #{gift_id}"
            await database.log_action(
                tg_id, "shop_buy_gift",
                f"Куплен подарок '{gift_name}' в магазине [{data.item_id}]", -price
            )

    else:
        raise HTTPException(status_code=400, detail="unknown_item_type")

    updated = await database.get_user_data(tg_id)
    return {
        "status":  "ok",
        "balance": updated.get("balance", 0),
        "stars":   updated.get("stars", 0),
  }
