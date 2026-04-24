# handlers/admin_bank.py
# Commands: /bankhelp, /bankstatus, /addbank
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

import config
import database
from .admin_constants import (
    E_DONUT, E_STAR, E_STOP, E_CHECK,
    E_MONEY, E_BANK, E_DROP, E_BOX, E_CHART,
    E_GIFT, E_CROSS,
)


def register(dp: Dispatcher, bot: Bot):

    @dp.message(Command("bankhelp"))
    async def cmd_bank_help(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(
                f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}",
                parse_mode="HTML",
            )
            return

        await message.answer(
            f"<b>{E_MONEY} Команды управления банком</b>\n\n"
            "<b>/bankstatus</b> — текущая ликвидность банка и RTP по всем валютам\n\n"
            "<b>/addbank &lt;сумма&gt; [stars|donuts]</b> — пополнить банк\n"
            "  Примеры:\n"
            "  <code>/addbank 500</code> — +500 звёзд (по умолчанию)\n"
            "  <code>/addbank 1000 donuts</code> — +1000 пончиков\n"
            "  <code>/addbank 200 stars</code> — +200 звёзд",
            parse_mode="HTML",
        )

    # ──────────────────────────────────────────────────────────────────────────

    @dp.message(Command("bankstatus"))
    async def cmd_bank_status(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(
                f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}",
                parse_mode="HTML",
            )
            return

        bank = await database.get_bank()

        stars_bal  = bank.get("stars_balance", 0)
        donuts_bal = bank.get("donuts_balance", 0)
        gift_bal   = bank.get("gift_value_balance", 0)

        total_dep  = bank.get("total_deposited_value", 0)
        total_paid = bank.get("total_paid_out_value", 0)
        total_edge = bank.get("total_house_edge_value", 0)

        stars_dep   = bank.get("stars_deposited", 0)
        stars_paid  = bank.get("stars_paid_out", 0)
        donuts_dep  = bank.get("donuts_deposited", 0)
        donuts_paid = bank.get("donuts_paid_out", 0)
        gift_paid   = bank.get("gift_value_paid_out", 0)

        def rtp(paid, dep):
            return f"{round(paid / dep * 100, 1)}%" if dep > 0 else "—"

        rate            = config.DONUTS_TO_STARS_RATE
        donuts_in_stars = donuts_bal * rate
        total_liq_stars = stars_bal + donuts_in_stars + gift_bal

        await message.answer(
            f"<b>{E_BANK} Состояние Глобального Банка</b>\n"
            f"<i>Курс: 1 {E_DONUT} = {rate} {E_STAR}</i>\n\n"
            f"<b>{E_DROP} Ликвидность</b>\n"
            f"  {E_STAR} Звёзды:              <b>{stars_bal}</b>\n"
            f"  {E_DONUT} Пончики:             <b>{donuts_bal}</b>\n"
            f"  {E_DONUT}→{E_STAR} Пончики в звёздах: <b>{donuts_in_stars}</b>\n"
            f"  {E_GIFT} Подарки (value):     <b>{gift_bal}</b>\n"
            f"  {E_BOX} Итого (stars-value): <b>{total_liq_stars}</b>\n\n"
            f"<b>{E_CHART} Общая статистика (все валюты)</b>\n"
            f"  Внесено:     {total_dep}\n"
            f"  Выплачено:   {total_paid}\n"
            f"  Комиссия:    {total_edge}\n"
            f"  RTP:         <b>{rtp(total_paid, total_dep)}</b>\n\n"
            f"<b>{E_STAR} Звёзды</b>\n"
            f"  Внесено: {stars_dep}  |  Выплачено: {stars_paid}"
            f"  |  RTP: <b>{rtp(stars_paid, stars_dep)}</b>\n\n"
            f"<b>{E_DONUT} Пончики</b>\n"
            f"  Внесено: {donuts_dep}  |  Выплачено: {donuts_paid}"
            f"  |  RTP: <b>{rtp(donuts_paid, donuts_dep)}</b>\n\n"
            f"<b>{E_GIFT} Подарки (value-эквивалент)</b>\n"
            f"  Выплачено: {gift_paid}",
            parse_mode="HTML",
        )

    # ──────────────────────────────────────────────────────────────────────────

    @dp.message(Command("addbank"))
    async def cmd_add_bank(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(
                f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}",
                parse_mode="HTML",
            )
            return

        args = message.text.split()
        if len(args) < 2 or len(args) > 3:
            await message.answer(
                "Использование: <code>/addbank &lt;сумма&gt; [stars|donuts]</code>\n"
                "По умолчанию — звёзды.\n\n"
                "Примеры:\n"
                "<code>/addbank 500</code>\n"
                "<code>/addbank 1000 donuts</code>",
                parse_mode="HTML",
            )
            return

        try:
            amount = int(args[1])
        except ValueError:
            await message.answer(f"{E_CROSS} Сумма должна быть целым числом.", parse_mode="HTML")
            return

        if amount <= 0:
            await message.answer(f"{E_CROSS} Сумма должна быть больше нуля.", parse_mode="HTML")
            return

        asset_type = "stars"
        if len(args) == 3:
            asset_type = args[2].lower()
            if asset_type not in ("stars", "donuts"):
                await message.answer(
                    f"{E_CROSS} Тип актива должен быть <code>stars</code> или <code>donuts</code>.",
                    parse_mode="HTML",
                )
                return

        if asset_type == "donuts":
            await database.bank_add_donuts(amount)
            label = f"{amount} {E_DONUT} пончиков"
        else:
            await database.bank_add_stars(amount)
            label = f"{amount} {E_STAR} звёзд"

        bank  = await database.get_bank()
        _rate = config.DONUTS_TO_STARS_RATE
        total_liq = (
            bank.get("stars_balance", 0)
            + bank.get("donuts_balance", 0) * _rate
            + bank.get("gift_value_balance", 0)
        )

        await message.answer(
            f"{E_CHECK} Банк пополнен на <b>{label}</b>.\n\n"
            f"{E_STAR} Звёзды: <b>{bank.get('stars_balance', 0)}</b>\n"
            f"{E_DONUT} Пончики: <b>{bank.get('donuts_balance', 0)}</b>"
            f" (≈ <b>{bank.get('donuts_balance', 0) * _rate}</b> {E_STAR})\n"
            f"{E_BOX} Общая ликвидность (в {E_STAR}): <b>{total_liq}</b>",
            parse_mode="HTML",
        )
