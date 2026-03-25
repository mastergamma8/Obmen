# handlers/admin.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import config
import database


class SendMessage(StatesGroup):
    waiting_for_target = State()
    waiting_for_message = State()


def register(dp: Dispatcher, bot: Bot):

    @dp.message(Command("addgift"))
    async def cmd_add_gift(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"⛔ У вас нет прав. Ваш ID: {message.from_user.id}")
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
            amount = int(args[3])

            profile_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👀 Посмотреть в профиле", web_app=WebAppInfo(url=config.WEBAPP_URL))]
            ])

            if gift_id in config.BASE_GIFTS:
                await message.answer("⏳ Получаю актуальную цену из API...")
                await asyncio.to_thread(config.update_base_gifts_prices)

                fresh_value = config.BASE_GIFTS[gift_id]['value']
                points_to_add = amount * fresh_value
                gift_name = config.BASE_GIFTS[gift_id]['name']

                await database.add_points_to_user(user_id, points_to_add)
                await database.add_history_entry(
                    user_id, "gift_added", f"Добавлен подарок: {gift_name} ({amount} шт.)", points_to_add
                )

                await message.answer(
                    f"✅ Успешно!\n"
                    f"Пользователю {user_id} начислено <b>{points_to_add} 🍩</b> "
                    f"(за {amount} шт. '{gift_name}' по актуальной цене <b>{fresh_value} 🍩/шт.</b>).",
                    parse_mode="HTML"
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"🎁 <b>Получен новый подарок!</b>\n<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Вам начислено <b>{points_to_add} 🍩</b>!",
                        parse_mode="HTML",
                        reply_markup=profile_markup
                    )
                except Exception as e:
                    logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

                # Реферальная система 10%
                referrer_id = await database.get_referrer(user_id)
                if referrer_id:
                    ref_bonus = max(1, int(points_to_add * 0.1))
                    await database.add_points_to_user(referrer_id, ref_bonus)
                    await database.add_history_entry(
                        referrer_id, "referral_bonus", "Реферальный бонус от подарка друга", ref_bonus
                    )
                    try:
                        await bot.send_message(
                            referrer_id,
                            f"🥳 Ваш реферал добавил подарок!\nВам начислено <b>{ref_bonus} 🍩</b> (10% бонус).",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

            elif gift_id in config.MAIN_GIFTS:
                await database.add_gift_to_user(user_id, gift_id, amount)
                gift_name = config.MAIN_GIFTS[gift_id]['name']
                await message.answer(
                    f"✅ Успешно!\nПользователю {user_id} выдан Главный подарок '{gift_name}' ({amount} шт.)."
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"🎁 <b>Вы получили подарок!</b>\n<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Зайдите в приложение, чтобы увидеть его в профиле!",
                        parse_mode="HTML",
                        reply_markup=profile_markup
                    )
                except Exception as e:
                    logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

            else:
                await message.answer(f"Подарок с ID {gift_id} не найден в config.py.")

        except ValueError:
            await message.answer("Ошибка: ID и Количество должны быть числами.")

    @dp.message(Command("addstars"))
    async def cmd_add_stars(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"⛔ У вас нет прав. Ваш ID: {message.from_user.id}")
            return

        args = message.text.split()
        if len(args) != 3:
            await message.answer(
                "Использование: /addstars <ID пользователя> <Количество>\n"
                "Пример: /addstars 123456789 50"
            )
            return

        try:
            user_id = int(args[1])
            stars_amount = int(args[2])

            if stars_amount <= 0:
                await message.answer("Количество звезд должно быть больше нуля.")
                return

            await database.add_stars_to_user(user_id, stars_amount)
            await database.add_history_entry(
                user_id, "admin_add_stars", "Выдача звезд администратором", stars_amount
            )

            await message.answer(f"✅ Успешно!\nПользователю {user_id} начислено {stars_amount} ⭐️.")

            try:
                profile_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👀 Посмотреть баланс", web_app=WebAppInfo(url=config.WEBAPP_URL))]
                ])
                await bot.send_message(
                    user_id,
                    f"🌟 <b>Вам начислены звезды!</b>\nАдминистратор выдал вам <b>{stars_amount} ⭐️</b>.",
                    parse_mode="HTML",
                    reply_markup=profile_markup
                )
            except Exception as e:
                logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

        except ValueError:
            await message.answer("Ошибка: ID и Количество должны быть числами.")

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is None:
            return
        await state.clear()
        await message.answer("Действие отменено.")

    @dp.message(Command("send"))
    async def cmd_send(message: Message, state: FSMContext):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer("⛔ У вас нет прав.")
            return
        await message.answer(
            "Кому отправить сообщение? Напишите слово <b>всем</b> или отправьте <b>ID пользователя</b>.\n"
            "<i>(Для отмены введите /cancel)</i>",
            parse_mode="HTML"
        )
        await state.set_state(SendMessage.waiting_for_target)

    @dp.message(SendMessage.waiting_for_target)
    async def process_send_target(message: Message, state: FSMContext):
        text = message.text.lower().strip() if message.text else ""
        if text == "всем":
            await state.update_data(target="all")
        elif text.isdigit():
            await state.update_data(target=int(text))
        else:
            await message.answer("Пожалуйста, напишите 'всем' или числовой ID.")
            return
        await message.answer(
            "Отлично! Теперь отправьте само сообщение. "
            "Вы можете прикрепить фото, видео, и использовать любое форматирование текста."
        )
        await state.set_state(SendMessage.waiting_for_message)

    @dp.message(SendMessage.waiting_for_message)
    async def process_send_message(message: Message, state: FSMContext):
        data = await state.get_data()
        target = data.get("target")
        await state.clear()
        await message.answer("⏳ Начинаю отправку...")

        success_count, fail_count = 0, 0
        if target == "all":
            users = await database.get_all_user_ids()
            for user_id in users:
                try:
                    await message.copy_to(chat_id=user_id)
                    success_count += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    fail_count += 1
            await message.answer(
                f"✅ Рассылка завершена!\nУспешно доставлено: {success_count}\nОшибок: {fail_count}"
            )
        else:
            try:
                await message.copy_to(chat_id=target)
                await message.answer(f"✅ Сообщение успешно доставлено пользователю {target}!")
            except Exception as e:
                await message.answer(f"❌ Ошибка при отправке.\nДетали: {e}")
