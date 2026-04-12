# handlers/admin.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.enums import ButtonStyle
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import config
import database

# --- Константы Премиум эмодзи для текста сообщений ---
E_DONUT = '<tg-emoji emoji-id="5354980321462885651">🍩</tg-emoji>'
E_GIFT = '<tg-emoji emoji-id="5963213811597970978">🎁</tg-emoji>'
E_STAR = '<tg-emoji emoji-id="5897920748101571572">⭐</tg-emoji>'
E_EYES = '<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji>'
E_STOP = '<tg-emoji emoji-id="5260293700088511294">⛔</tg-emoji>'
E_CHECK = '<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji>'
E_PARTY = '<tg-emoji emoji-id="5461151367559141950">🥳</tg-emoji>'
E_MONEY = '<tg-emoji emoji-id="5409048419211682843">💰</tg-emoji>'
E_BANK = '<tg-emoji emoji-id="5264895611517300926">🏦</tg-emoji>'
E_DROP = '<tg-emoji emoji-id="5393512611968995988">💧</tg-emoji>'
E_BOX = '<tg-emoji emoji-id="5884479287171485878">📦</tg-emoji>'
E_CHART = '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>'
E_CROSS = '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>'
E_TIME = '<tg-emoji emoji-id="5386367538735104399">⏳</tg-emoji>'

# --- ID для иконок на кнопках ---
ID_EYES = "5210956306952758910"
ID_STAR = "5897920748101571572"


class SendMessage(StatesGroup):
    waiting_for_target = State()
    waiting_for_message = State()


def register(dp: Dispatcher, bot: Bot):

    @dp.message(Command("addgift"))
    async def cmd_add_gift(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}", parse_mode="HTML")
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

            # Кнопка теперь зеленая и с премиум иконкой глаз
            profile_markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Посмотреть в профиле", 
                        web_app=WebAppInfo(url=config.WEBAPP_URL),
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=ID_EYES
                    )
                ]
            ])

            if gift_id in config.BASE_GIFTS:
                await message.answer(f"{E_TIME} Получаю актуальную цену из API...", parse_mode="HTML")
                await asyncio.to_thread(config.update_base_gifts_prices)

                fresh_value = config.BASE_GIFTS[gift_id]['value']
                points_to_add = amount * fresh_value
                gift_name = config.BASE_GIFTS[gift_id]['name']

                await database.add_points_to_user(user_id, points_to_add)
                await database.add_history_entry(
                    user_id, "gift_added", f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]", points_to_add
                )

                await message.answer(
                    f"{E_CHECK} Успешно!\n"
                    f"Пользователю {user_id} начислено <b>{points_to_add} {E_DONUT}</b> "
                    f"(за {amount} шт. '{gift_name}' по актуальной цене <b>{fresh_value} {E_DONUT}/шт.</b>).",
                    parse_mode="HTML"
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"{E_GIFT} <b>Получен новый подарок!</b>\n<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Вам начислено <b>{points_to_add} {E_DONUT}</b>!",
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
                            f"{E_PARTY} Ваш реферал добавил подарок!\nВам начислено <b>{ref_bonus} {E_DONUT}</b> (10% бонус).",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

            elif gift_id in getattr(config, "TG_GIFTS", {}):
                await database.add_gift_to_user(user_id, gift_id, amount)
                gift_name = config.TG_GIFTS[gift_id]['name']
                await database.add_history_entry(
                    user_id, "gift_added", f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]", 0
                )
                await message.answer(
                    f"{E_CHECK} Успешно!\nПользователю {user_id} выдан Telegram-подарок '{gift_name}' ({amount} шт.).",
                    parse_mode="HTML"
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"{E_GIFT} <b>Вы получили подарок!</b>\n<b>{gift_name}</b> ({amount} шт.).\n"
                        f"Зайдите в приложение, чтобы увидеть его в профиле!",
                        parse_mode="HTML",
                        reply_markup=profile_markup
                    )
                except Exception as e:
                    logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

            elif gift_id in config.MAIN_GIFTS:
                await database.add_gift_to_user(user_id, gift_id, amount)
                gift_name = config.MAIN_GIFTS[gift_id]['name']
                await database.add_history_entry(
                    user_id, "gift_added", f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]", 0
                )
                await message.answer(
                    f"{E_CHECK} Успешно!\nПользователю {user_id} выдан Главный подарок '{gift_name}' ({amount} шт.).",
                    parse_mode="HTML"
                )

                try:
                    await bot.send_message(
                        user_id,
                        f"{E_GIFT} <b>Вы получили подарок!</b>\n<b>{gift_name}</b> ({amount} шт.).\n"
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
            await message.answer(f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}", parse_mode="HTML")
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

            await message.answer(f"{E_CHECK} Успешно!\nПользователю {user_id} начислено {stars_amount} {E_STAR}.", parse_mode="HTML")

            try:
                # Кнопка зеленая с премиум иконкой звезды
                profile_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Посмотреть баланс", 
                            web_app=WebAppInfo(url=config.WEBAPP_URL),
                            style=ButtonStyle.SUCCESS,
                            icon_custom_emoji_id=ID_STAR
                        )
                    ]
                ])
                await bot.send_message(
                    user_id,
                    f"{E_STAR} <b>Вам начислены звезды!</b>\nАдминистратор выдал вам <b>{stars_amount} {E_STAR}</b>.",
                    parse_mode="HTML",
                    reply_markup=profile_markup
                )
            except Exception as e:
                logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

        except ValueError:
            await message.answer("Ошибка: ID и Количество должны быть числами.")

    @dp.message(Command("bankhelp"))
    async def cmd_bank_help(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}", parse_mode="HTML")
            return
        await message.answer(
            f"<b>{E_MONEY} Команды управления банком</b>\n\n"
            "<b>/bankstatus</b> — текущая ликвидность банка и RTP по всем валютам\n\n"
            "<b>/addbank &lt;сумма&gt; [stars|donuts]</b> — пополнить банк\n"
            "  Примеры:\n"
            "  <code>/addbank 500</code> — +500 звёзд (по умолчанию)\n"
            "  <code>/addbank 1000 donuts</code> — +1000 пончиков\n"
            "  <code>/addbank 200 stars</code> — +200 звёзд",
            parse_mode="HTML"
        )

    @dp.message(Command("bankstatus"))
    async def cmd_bank_status(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}", parse_mode="HTML")
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
            f"  Внесено: {stars_dep}  |  Выплачено: {stars_paid}  |  RTP: <b>{rtp(stars_paid, stars_dep)}</b>\n\n"
            f"<b>{E_DONUT} Пончики</b>\n"
            f"  Внесено: {donuts_dep}  |  Выплачено: {donuts_paid}  |  RTP: <b>{rtp(donuts_paid, donuts_dep)}</b>\n\n"
            f"<b>{E_GIFT} Подарки (value-эквивалент)</b>\n"
            f"  Выплачено: {gift_paid}",
            parse_mode="HTML"
        )

    @dp.message(Command("addbank"))
    async def cmd_add_bank(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав. Ваш ID: {message.from_user.id}", parse_mode="HTML")
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
            await message.answer(f"{E_CROSS} Сумма должна быть целым числом.", parse_mode="HTML")
            return

        if amount <= 0:
            await message.answer(f"{E_CROSS} Сумма должна быть больше нуля.", parse_mode="HTML")
            return

        asset_type = "stars"
        if len(args) == 3:
            asset_type = args[2].lower()
            if asset_type not in ("stars", "donuts"):
                await message.answer(f"{E_CROSS} Тип актива должен быть <code>stars</code> или <code>donuts</code>.", parse_mode="HTML")
                return

        if asset_type == "donuts":
            await database.bank_add_donuts(amount)
            label = f"{amount} {E_DONUT} пончиков"
        else:
            await database.bank_add_stars(amount)
            label = f"{amount} {E_STAR} звёзд"

        bank = await database.get_bank()
        import config as _cfg
        _rate = _cfg.DONUTS_TO_STARS_RATE
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
            parse_mode="HTML"
        )

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
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
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
        await message.answer(f"{E_TIME} Начинаю отправку...", parse_mode="HTML")

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
                f"{E_CHECK} Рассылка завершена!\nУспешно доставлено: {success_count}\nОшибок: {fail_count}",
                parse_mode="HTML"
            )
        else:
            try:
                await message.copy_to(chat_id=target)
                await message.answer(f"{E_CHECK} Сообщение успешно доставлено пользователю {target}!", parse_mode="HTML")
            except Exception as e:
                await message.answer(f"{E_CROSS} Ошибка при отправке.\nДетали: {e}", parse_mode="HTML")
    @dp.message(Command("setexchangerate"))
    async def cmd_set_exchange_rate(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) != 2:
            current = getattr(config, "GIFT_EXCHANGE_STARS_RATE", "не задан")
            await message.answer(
                f"<b>Курс обмена подарков на звёзды</b>\n\n"
                f"Текущий курс: <b>{current} ⭐ за 1 🍩</b>\n\n"
                f"Использование: <code>/setexchangerate &lt;значение&gt;</code>\n"
                f"Пример: <code>/setexchangerate 0.015</code>\n\n"
                f"<i>Подарок стоимостью 1000 🍩 при курсе 0.01 = 10 ⭐</i>",
                parse_mode="HTML"
            )
            return

        try:
            new_rate = float(args[1])
            if new_rate <= 0:
                await message.answer(f"{E_CROSS} Курс должен быть больше нуля.", parse_mode="HTML")
                return
            if new_rate > 100:
                await message.answer(f"{E_CROSS} Курс не может быть больше 100.", parse_mode="HTML")
                return

            old_rate = getattr(config, "GIFT_EXCHANGE_STARS_RATE", "?")
            config.GIFT_EXCHANGE_STARS_RATE = new_rate

            await message.answer(
                f"{E_CHECK} <b>Курс обмена обновлён!</b>\n\n"
                f"Было: <b>{old_rate}</b>\n"
                f"Стало: <b>{new_rate} ⭐ за 1 🍩</b>",
                parse_mode="HTML"
            )
        except ValueError:
            await message.answer(
                f"{E_CROSS} Некорректное значение. Введите число, например: <code>0.015</code>",
                parse_mode="HTML"
            )

    @dp.message(Command("genfakeusers"))
    async def cmd_gen_fake_users(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        import random
        import time
        import aiosqlite
        from db.db_core import DB_NAME

        FAKE_NAMES = [
            "Алексей", "Мария", "Дмитрий", "Анна", "Сергей", "Екатерина",
            "Иван", "Ольга", "Андрей", "Наталья", "Михаил", "Татьяна",
            "Николай", "Юлия", "Артём", "Елена", "Кирилл", "Ирина",
            "Владимир", "Светлана", "Павел", "Ксения", "Роман", "Виктория",
            "Денис", "Людмила", "Евгений", "Дарья", "Антон", "Полина",
            "Максим", "Валерия", "Тимур", "Алина", "Глеб", "Вероника",
            "Илья", "Маргарита", "Руслан", "Кристина", "Степан", "Диана",
            "Константин", "Надежда", "Юрий", "Милана", "Геннадий", "Таисия",
            "Борис", "Регина",
        ]
        AVATARS = [
            "https://i.pravatar.cc/150?img={}".format(i) for i in range(1, 71)
        ]

        await message.answer(f"{E_TIME} Генерирую 100 фейковых пользователей...", parse_mode="HTML")

        now = int(time.time())
        week_ago = now - 6 * 86400  # в пределах последней недели

        fake_tg_id_start = 9_000_000_000  # диапазон, не пересекающийся с реальными

        async with aiosqlite.connect(DB_NAME) as db:
            for i in range(100):
                tg_id    = fake_tg_id_start + i
                name     = random.choice(FAKE_NAMES) + f"_{i+1}"
                username = f"fake_user_{i+1}"
                avatar   = random.choice(AVATARS)
                balance  = random.randint(10, 50_000)

                # Вставка пользователя
                await db.execute("""
                    INSERT INTO users (
                        tg_id, username, first_name, photo_url,
                        balance, stars, last_free_spin, notified_free_spin,
                        last_gift_withdraw, notified_gift_withdraw,
                        last_gift_claim, notified_gift_claim,
                        last_free_case, notified_free_case
                    )
                    VALUES (?, ?, ?, ?, ?, 0, 0, 1, 0, 1, 0, 1, 0, 1)
                    ON CONFLICT(tg_id) DO UPDATE SET
                        username=excluded.username,
                        first_name=excluded.first_name,
                        photo_url=excluded.photo_url,
                        balance=excluded.balance
                """, (tg_id, username, name, avatar, balance))

                # Ракета — случайный множитель для ~70% фейков
                if random.random() < 0.7:
                    multiplier = round(random.uniform(1.2, 50.0), 2)
                    ts = random.randint(week_ago, now)
                    await db.execute("""
                        INSERT INTO user_history (user_id, action_type, description, amount, created_at)
                        VALUES (?, 'rocket_win_fake', ?, ?, ?)
                    """, (tg_id, f"Ракета: x{multiplier}", int(multiplier * 100), ts))

                # Кейс — случайный коэффициент для ~60% фейков
                if random.random() < 0.6:
                    ratio_x100 = random.randint(110, 2000)  # от 1.10x до 20.00x
                    await db.execute("""
                        INSERT INTO user_history (user_id, action_type, description, amount, created_at)
                        VALUES (?, 'case_lucky_ratio', 'Фейк: кейс', ?, ?)
                    """, (tg_id, ratio_x100, random.randint(week_ago, now)))

            await db.commit()

        await message.answer(
            f"{E_CHECK} <b>Готово!</b>\n\n"
            f"Создано <b>100 фейковых пользователей</b> (tg_id {fake_tg_id_start}–{fake_tg_id_start + 99}).\n"
            f"Данные добавлены во все три таблицы лидеров.\n\n"
            f"<i>Для удаления фейков используйте /delfakeusers</i>",
            parse_mode="HTML"
        )

    @dp.message(Command("delfakeusers"))
    async def cmd_del_fake_users(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        import aiosqlite
        from db.db_core import DB_NAME

        fake_tg_id_start = 9_000_000_000
        fake_tg_id_end   = fake_tg_id_start + 99

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "DELETE FROM user_history WHERE user_id BETWEEN ? AND ?",
                (fake_tg_id_start, fake_tg_id_end)
            )
            result = await db.execute(
                "DELETE FROM users WHERE tg_id BETWEEN ? AND ?",
                (fake_tg_id_start, fake_tg_id_end)
            )
            deleted = result.rowcount
            await db.commit()

        await message.answer(
            f"{E_CHECK} Удалено <b>{deleted}</b> фейковых пользователей и их история.",
            parse_mode="HTML"
        )
