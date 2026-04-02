# handlers/start.py
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)

import config
import database
from db.db_referrals import distribute_referral_bonus_stars


def register(dp: Dispatcher, bot: Bot):

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        user_id = message.from_user.id
        logging.info(f"Пользователь {user_id} нажал /start")

        args = message.text.split()
        referrer_id = None
        if len(args) > 1 and args[1].isdigit():
            referrer_id = int(args[1])

        try:
            await database.upsert_user(
                tg_id=user_id,
                username=message.from_user.username or "",
                first_name=message.from_user.first_name or "Без имени",
                photo_url=""
            )

            if referrer_id:
                await database.set_referrer(user_id, referrer_id)

            if not config.WEBAPP_URL.startswith("https://"):
                await message.answer("⚠️ Ошибка: WEBAPP_URL в config.py должен начинаться с https://")
                return

            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=config.WEBAPP_URL))]
            ])

            text = "Привет! Нажми на кнопку ниже, чтобы открыть приложение."
            if referrer_id and referrer_id != user_id:
                text += "\n\n🎉 Вы перешли по пригласительной ссылке!"

            await message.answer(text, reply_markup=markup)

        except Exception as e:
            logging.error(f"Ошибка в /start: {e}")

    @dp.pre_checkout_query()
    async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    @dp.message(F.successful_payment)
    async def process_successful_payment(message: Message):
        payload = message.successful_payment.invoice_payload
        if payload.startswith("topup_"):
            parts = payload.split("_")
            if len(parts) == 3:
                user_id = int(parts[1])
                stars_amount = int(parts[2])

                # Защита от подмены: реальный плательщик должен совпадать
                # с user_id из payload, чтобы нельзя было зачислить звёзды чужому аккаунту.
                if message.from_user.id != user_id:
                    logging.warning(
                        f"successful_payment mismatch: from_user={message.from_user.id}, "
                        f"payload_user={user_id} — начисление отклонено"
                    )
                    await message.answer("❌ Ошибка верификации платежа. Обратитесь в поддержку.")
                    return

                await database.add_stars_to_user(user_id, stars_amount)
                await database.add_history_entry(
                    user_id, "topup_stars", f"Пополнение баланса на {stars_amount} ⭐️", stars_amount
                )

                # Реферальный бонус: 10% от пополнения звёздами пригласившему
                await distribute_referral_bonus_stars(user_id, stars_amount)

                await message.answer(
                    f"🎉 <b>Успешно!</b>\nВаш баланс пополнен на <b>{stars_amount} ⭐️</b>!",
                    parse_mode="HTML"
                )