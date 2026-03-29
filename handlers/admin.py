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

    # ── Банк: справка ─────────────────────────────────────────────────────────

    @dp.message(Command("bankhelp"))
    async def cmd_bank_help(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"⛔ У вас нет прав. Ваш ID: {message.from_user.id}")
            return
        await message.answer(
            "<b>💰 Команды управления банком</b>\n\n"
            "<b>/bankstatus</b> — текущая ликвидность банка и RTP по всем валютам\n\n"
            "<b>/addbank &lt;сумма&gt; [stars|donuts]</b> — пополнить банк\n"
            "  Примеры:\n"
            "  <code>/addbank 500</code> — +500 звёзд (по умолчанию)\n"
            "  <code>/addbank 1000 donuts</code> — +1000 пончиков\n"
            "  <code>/addbank 200 stars</code> — +200 звёзд",
            parse_mode="HTML"
        )

    # ── Банк: статус ──────────────────────────────────────────────────────────

    @dp.message(Command("bankstatus"))
    async def cmd_bank_status(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"⛔ У вас нет прав. Ваш ID: {message.from_user.id}")
            return

        bank = await database.get_bank()

        stars_bal  = bank.get("stars_balance", 0)
        donuts_bal = bank.get("donuts_balance", 0)
        gift_bal   = bank.get("gift_value_balance", 0)
        total_liq  = stars_bal + donuts_bal + gift_bal

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

        rate = config.DONUTS_TO_STARS_RATE
        donuts_in_stars = donuts_bal * rate
        total_liq_stars = stars_bal + donuts_in_stars + gift_bal
        await message.answer(
            "<b>🏦 Состояние Глобального Банка</b>\n"
            f"<i>Курс: 1 🍩 = {rate} ⭐️</i>\n\n"
            "<b>💧 Ликвидность</b>\n"
            f"  ⭐️ Звёзды:              <b>{stars_bal}</b>\n"
            f"  🍩 Пончики:             <b>{donuts_bal}</b>\n"
            f"  🍩→⭐️ Пончики в звёздах: <b>{donuts_in_stars}</b>\n"
            f"  🎁 Подарки (value):     <b>{gift_bal}</b>\n"
            f"  📦 Итого (stars-value): <b>{total_liq_stars}</b>\n\n"
            "<b>📊 Общая статистика (все валюты)</b>\n"
            f"  Внесено:     {total_dep}\n"
            f"  Выплачено:   {total_paid}\n"
            f"  Комиссия:    {total_edge}\n"
            f"  RTP:         <b>{rtp(total_paid, total_dep)}</b>\n\n"
            "<b>⭐️ Звёзды</b>\n"
            f"  Внесено: {stars_dep}  |  Выплачено: {stars_paid}  |  RTP: <b>{rtp(stars_paid, stars_dep)}</b>\n\n"
            "<b>🍩 Пончики</b>\n"
            f"  Внесено: {donuts_dep}  |  Выплачено: {donuts_paid}  |  RTP: <b>{rtp(donuts_paid, donuts_dep)}</b>\n\n"
            "<b>🎁 Подарки (value-эквивалент)</b>\n"
            f"  Выплачено: {gift_paid}",
            parse_mode="HTML"
        )

    # ── Банк: пополнение ──────────────────────────────────────────────────────

    @dp.message(Command("addbank"))
    async def cmd_add_bank(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"⛔ У вас нет прав. Ваш ID: {message.from_user.id}")
            return

        args = message.text.split()
        if len(args) < 2 or len(args) > 3:
            await message.answer(
                "Использование: <code>/addbank &lt;сумма&gt; [stars|donuts]</code>\n"
                "По умолчанию — звёзды.\n\n"
                "Примеры:\n"
                "<code>/addbank 500</code>\n"
                "<code>/addbank 1000 donuts</code>",
                parse_mode="HTML"
            )
            return

        try:
            amount = int(args[1])
        except ValueError:
            await message.answer("❌ Сумма должна быть целым числом.")
            return

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля.")
            return

        asset_type = "stars"
        if len(args) == 3:
            asset_type = args[2].lower()
            if asset_type not in ("stars", "donuts"):
                await message.answer("❌ Тип актива должен быть <code>stars</code> или <code>donuts</code>.", parse_mode="HTML")
                return

        if asset_type == "donuts":
            await database.bank_add_donuts(amount)
            label = f"{amount} 🍩 пончиков"
        else:
            await database.bank_add_stars(amount)
            label = f"{amount} ⭐️ звёзд"

        bank = await database.get_bank()
        total_liq = (
            bank.get("stars_balance", 0)
            + bank.get("donuts_balance", 0)
            + bank.get("gift_value_balance", 0)
        )

        await message.answer(
            f"✅ Банк пополнен на <b>{label}</b>.\n\n"
            f"⭐️ Звёзды: <b>{bank.get('stars_balance', 0)}</b>\n"
            f"🍩 Пончики: <b>{bank.get('donuts_balance', 0)}</b>\n"
            f"📦 Общая ликвидность: <b>{total_liq}</b>",
            parse_mode="HTML"
        )

    # ── Отмена FSM ────────────────────────────────────────────────────────────

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
