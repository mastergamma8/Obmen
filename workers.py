# workers.py
import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import config
import database


async def roulette_reminder_worker(bot: Bot):
    """Уведомляет пользователей, когда бесплатная прокрутка рулетки снова доступна."""
    while True:
        try:
            now = int(__import__('time').time())
            users_to_notify = await database.get_users_to_notify(now)

            if users_to_notify:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Крутить рулетку", web_app=WebAppInfo(url=config.WEBAPP_URL))]
                ])
                text = (
                    "🎁 Напоминание! Твоя бесплатная прокрутка рулетки снова доступна.\n\n"
                    "Заходи в приложение и забирай свои награды!"
                )

                for user_id in users_to_notify:
                    try:
                        await bot.send_message(user_id, text, reply_markup=markup)
                        await database.mark_user_notified(user_id)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.warning(f"Не удалось отправить напоминание {user_id}: {e}")
                        await database.mark_user_notified(user_id)
        except Exception as e:
            logging.error(f"Ошибка в воркере напоминаний рулетки: {e}")

        await asyncio.sleep(300)


async def gift_claim_reminder_worker(bot: Bot):
    """Уведомляет пользователей, когда кулдаун покупки подарка с главной страницы истёк."""
    while True:
        try:
            now = int(__import__('time').time())
            users_to_notify = await database.get_users_to_notify_gift_claim(now)

            if users_to_notify:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎁 Купить подарок", web_app=WebAppInfo(url=config.WEBAPP_URL))]
                ])
                text = (
                    "🛒 <b>Ограничение на покупку снято!</b>\n\n"
                    "Вы снова можете покупать подарки за пончики. Заходите в приложение!"
                )

                for user_id in users_to_notify:
                    try:
                        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=markup)
                        await database.mark_user_notified_gift_claim(user_id)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.warning(f"Не удалось отправить уведомление о покупке {user_id}: {e}")
                        await database.mark_user_notified_gift_claim(user_id)
        except Exception as e:
            logging.error(f"Ошибка в воркере уведомлений о покупке: {e}")

        await asyncio.sleep(60)


async def gift_withdraw_reminder_worker(bot: Bot):
    """Уведомляет пользователей, когда кулдаун вывода подарка истёк."""
    while True:
        try:
            now = int(__import__('time').time())
            users_to_notify = await database.get_users_to_notify_gift_withdraw(now)

            if users_to_notify:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎁 Открыть приложение", web_app=WebAppInfo(url=config.WEBAPP_URL))]
                ])
                text = (
                    "🎁 <b>Вывод подарка снова доступен!</b>\n\n"
                    "Прошло 5 часов — вы можете купить или вывести новый подарок. "
                    "Заходите в приложение!"
                )

                for user_id in users_to_notify:
                    try:
                        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=markup)
                        await database.mark_user_notified_gift_withdraw(user_id)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.warning(f"Не удалось отправить уведомление о выводе {user_id}: {e}")
                        await database.mark_user_notified_gift_withdraw(user_id)
        except Exception as e:
            logging.error(f"Ошибка в воркере уведомлений о выводе: {e}")

        await asyncio.sleep(120)


async def free_case_reminder_worker(bot: Bot):
    """Уведомляет пользователей, когда бесплатный кейс снова доступен (24 ч кулдаун)."""
    while True:
        try:
            now = int(__import__('time').time())
            users_to_notify = await database.get_users_to_notify_free_case(now)

            if users_to_notify:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎁 Открыть бесплатный кейс", web_app=WebAppInfo(url=config.WEBAPP_URL))]
                ])
                text = (
                    "📦 <b>Бесплатный кейс снова доступен!</b>\n\n"
                    "Прошло 24 часа — заходи в приложение и открывай свой бесплатный кейс!"
                )

                for user_id in users_to_notify:
                    try:
                        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=markup)
                        await database.mark_user_notified_free_case(user_id)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.warning(f"Не удалось отправить уведомление о кейсе {user_id}: {e}")
                        await database.mark_user_notified_free_case(user_id)
        except Exception as e:
            logging.error(f"Ошибка в воркере уведомлений о бесплатном кейсе: {e}")

        await asyncio.sleep(300)


async def price_update_worker():
    """Обновляет цены подарков каждые 30 минут."""
    while True:
        await asyncio.sleep(1800)
        logging.info("⏱ Автоматическое обновление цен по таймеру (каждые 30 мин)...")
        try:
            await asyncio.to_thread(config.update_base_gifts_prices)
        except Exception as e:
            logging.error(f"Ошибка при автоматическом обновлении цен: {e}")