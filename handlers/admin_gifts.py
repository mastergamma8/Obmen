# handlers/admin_gifts.py
# Commands: /addgift, /addstars
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.enums import ButtonStyle
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)

import config
import database
from .admin_constants import (
    E_DONUT, E_GIFT, E_STAR, E_STOP, E_CHECK,
    E_PARTY, E_TIME, E_CROSS,
    ID_EYES, ID_STAR,
)


def register(dp: Dispatcher, bot: Bot):

    @dp.message(Command("addgift"))
    async def cmd_add_gift(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(
                f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}",
                parse_mode="HTML",
            )
            return

        args = message.text.split()
        if len(args) != 4:
            await message.answer(
                "Использование: /addgift <ID пользователя> <ID подарка> <Количество>\n"
                "Пример: /addgift 123456789 2 5"
            )
            return

        try:
            user_id = int(args[1])
            gift_id = int(args[2])
            amount  = int(args[3])

            if amount <= 0:
                await message.answer("Количество должно быть больше 0.")
                return

            profile_markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Посмотреть в профиле",
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                    style=ButtonStyle.SUCCESS,
                    icon_custom_emoji_id=ID_EYES,
                )
            ]])

            if gift_id in config.BASE_GIFTS:
                await message.answer(
                    f"{E_TIME} Получаю актуальную цену из API...", parse_mode="HTML"
                )
                await asyncio.to_thread(config.update_base_gifts_prices)

                fresh_value   = float(config.BASE_GIFTS[gift_id]["value"])
                points_to_add = round(amount * fresh_value, 4)
                gift_name     = config.BASE_GIFTS[gift_id]["name"]

                await database.add_points_to_user(user_id, points_to_add)
                await database.add_history_entry(
                    user_id, "gift_added",
                    f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]",
                    points_to_add,
                )

                await message.answer(
                    f"{E_CHECK} Успешно!\n"
                    f"Пользователю {user_id} начислено <b>{points_to_add} {E_DONUT}</b> "
                    f"(за {amount} шт. '{gift_name}' по актуальной цене"
                    f" <b>{fresh_value} {E_DONUT}/шт.</b>).",
                    parse_mode="HTML",
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"{E_GIFT} <b>Получен новый подарок!</b>\n"
                        f"<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Вам начислено <b>{points_to_add} {E_DONUT}</b>!",
                        parse_mode="HTML",
                        reply_markup=profile_markup,
                    )
                except Exception as e:
                    logging.warning(
                        f"Не удалось отправить уведомление пользователю {user_id}: {e}"
                    )

                referrer_id = await database.get_referrer(user_id)
                if referrer_id:
                    bonus = round(points_to_add * 0.10, 2)
                    if bonus > 0:
                        await database.distribute_referral_bonus(user_id, points_to_add)
                        try:
                            await bot.send_message(
                                referrer_id,
                                f"{E_PARTY} Ваш реферал добавил подарок!\n"
                                f"Вам начислено <b>{bonus} {E_DONUT}</b>"
                                f" (10% бонус за {gift_name}).",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass

            elif gift_id in getattr(config, "TG_GIFTS", {}):
                await database.add_gift_to_user(user_id, gift_id, amount)
                gift_name = config.TG_GIFTS[gift_id]["name"] or f"TG gift {gift_id}"

                await database.add_history_entry(
                    user_id, "gift_added",
                    f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]",
                    0,
                )
                await message.answer(
                    f"{E_CHECK} Успешно!\n"
                    f"Пользователю {user_id} выдан Telegram-подарок '{gift_name}' ({amount} шт.).",
                    parse_mode="HTML",
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"{E_GIFT} <b>Вы получили подарок!</b>\n"
                        f"<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Зайдите в приложение, чтобы увидеть его в профиле!",
                        parse_mode="HTML",
                        reply_markup=profile_markup,
                    )
                except Exception as e:
                    logging.warning(
                        f"Не удалось отправить уведомление пользователю {user_id}: {e}"
                    )

            elif gift_id in config.MAIN_GIFTS:
                await database.add_gift_to_user(user_id, gift_id, amount)
                gift_name = config.MAIN_GIFTS[gift_id]["name"]

                await database.add_history_entry(
                    user_id, "gift_added",
                    f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]",
                    0,
                )
                await message.answer(
                    f"{E_CHECK} Успешно!\n"
                    f"Пользователю {user_id} выдан Главный подарок '{gift_name}' ({amount} шт.).",
                    parse_mode="HTML",
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"{E_GIFT} <b>Вы получили подарок!</b>\n"
                        f"<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Зайдите в приложение, чтобы увидеть его в профиле!",
                        parse_mode="HTML",
                        reply_markup=profile_markup,
                    )
                except Exception as e:
                    logging.warning(
                        f"Не удалось отправить уведомление пользователю {user_id}: {e}"
                    )

            else:
                await message.answer(f"Подарок с ID {gift_id} не найден в config.py.")

        except ValueError:
            await message.answer("Ошибка: ID и Количество должны быть числами.")

    # ──────────────────────────────────────────────────────────────────────────

    @dp.message(Command("addstars"))
    async def cmd_add_stars(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(
                f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}",
                parse_mode="HTML",
            )
            return

        args = message.text.split()
        if len(args) != 3:
            await message.answer(
                "Использование: /addstars <ID пользователя> <Количество>\n"
                "Пример: /addstars 123456789 50"
            )
            return

        try:
            user_id      = int(args[1])
            stars_amount = int(args[2])

            if stars_amount <= 0:
                await message.answer("Количество звезд должно быть больше нуля.")
                return

            await database.add_stars_to_user(user_id, stars_amount)
            await database.add_history_entry(
                user_id, "admin_add_stars", "Выдача звезд администратором", stars_amount
            )

            await message.answer(
                f"{E_CHECK} Успешно!\nПользователю {user_id} начислено {stars_amount} {E_STAR}.",
                parse_mode="HTML",
            )

            try:
                profile_markup = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Посмотреть баланс",
                        web_app=WebAppInfo(url=config.WEBAPP_URL),
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=ID_STAR,
                    )
                ]])
                await bot.send_message(
                    user_id,
                    f"{E_STAR} <b>Вам начислены звезды!</b>\n"
                    f"Администратор выдал вам <b>{stars_amount} {E_STAR}</b>.",
                    parse_mode="HTML",
                    reply_markup=profile_markup,
                )
            except Exception as e:
                logging.warning(
                    f"Не удалось отправить уведомление пользователю {user_id}: {e}"
                )

        except ValueError:
            await message.answer("Ошибка: ID и Количество должны быть числами.")
