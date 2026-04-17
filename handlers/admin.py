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

            if amount <= 0:
                await message.answer("Количество должно быть больше 0.")
                return

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

                fresh_value = float(config.BASE_GIFTS[gift_id]['value'])
                points_to_add = round(amount * fresh_value, 4)
                gift_name = config.BASE_GIFTS[gift_id]['name']

                await database.add_points_to_user(user_id, points_to_add)
                await database.add_history_entry(
                    user_id, "gift_added",
                    f"Добавлен подарок: {gift_name} ({amount} шт.) [gift_id:{gift_id}]",
                    points_to_add
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

                referrer_id = await database.get_referrer(user_id)
                if referrer_id:
                    bonus = round(points_to_add * 0.10, 2)
                    if bonus > 0:
                        await database.distribute_referral_bonus(user_id, points_to_add)
                        try:
                            await bot.send_message(
                                referrer_id,
                                f"{E_PARTY} Ваш реферал добавил подарок!\n"
                                f"Вам начислено <b>{bonus} {E_DONUT}</b> (10% бонус за {gift_name}).",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass

            elif gift_id in getattr(config, "TG_GIFTS", {}):
                await database.add_gift_to_user(user_id, gift_id, amount)
                gift_name = config.TG_GIFTS[gift_id]['name'] or f"TG gift {gift_id}"

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


    @dp.message(Command("addpromo"))
    async def cmd_add_promo(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) < 5:
            await message.answer(
                "<b>Создание промокода</b>\n\n"
                "Использование:\n"
                "<code>/addpromo CODE donuts AMOUNT USES</code>\n"
                "<code>/addpromo CODE stars AMOUNT USES</code>\n"
                "<code>/addpromo CODE case CASE_ID USES</code>\n\n"
                "Примеры:\n"
                "<code>/addpromo DONUTS100 donuts 100 50</code>\n"
                "<code>/addpromo STAR10 stars 10 100</code>\n"
                "<code>/addpromo CASE7 case 7 25</code>",
                parse_mode="HTML"
            )
            return

        code = args[1].strip().upper()
        reward_type = args[2].strip().lower()

        try:
            if reward_type in ("donuts", "stars"):
                reward_value = int(args[3])
                max_uses = int(args[4])
                case_id = None
            elif reward_type == "case":
                case_id = int(args[3])
                max_uses = int(args[4])
                reward_value = 0
            else:
                await message.answer(f"{E_CROSS} Тип награды должен быть donuts, stars или case.", parse_mode="HTML")
                return
        except ValueError:
            await message.answer(f"{E_CROSS} AMOUNT / USES / CASE_ID должны быть числами.", parse_mode="HTML")
            return

        if max_uses <= 0:
            await message.answer(f"{E_CROSS} Количество активаций должно быть больше 0.", parse_mode="HTML")
            return

        if reward_type in ("donuts", "stars") and reward_value <= 0:
            await message.answer(f"{E_CROSS} Количество награды должно быть больше 0.", parse_mode="HTML")
            return

        if reward_type == "case" and case_id not in config.CASES_CONFIG:
            await message.answer(f"{E_CROSS} Кейса с ID {case_id} нет в конфиге.", parse_mode="HTML")
            return

        created = await database.create_promo_code(
            code=code,
            reward_type=reward_type,
            reward_value=reward_value,
            max_uses=max_uses,
            case_id=case_id,
            created_by=message.from_user.id,
        )

        if not created:
            await message.answer(f"{E_CROSS} Промокод <code>{code}</code> уже существует.", parse_mode="HTML")
            return

        if reward_type == "case":
            reward_text = f"бесплатный кейс <b>#{case_id}</b>"
        elif reward_type == "stars":
            reward_text = f"<b>{reward_value}</b> {E_STAR}"
        else:
            reward_text = f"<b>{reward_value}</b> {E_DONUT}"

        await message.answer(
            f"{E_CHECK} Промокод <code>{code}</code> создан.\n\n"
            f"Награда: {reward_text}\n"
            f"Активаций: <b>{max_uses}</b>",
            parse_mode="HTML"
        )

    @dp.message(Command("promos"))
    async def cmd_list_promos(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        promos = await database.get_all_promo_codes()
        if not promos:
            await message.answer("Промокодов пока нет.")
            return

        lines = ["<b>Активные промокоды</b>\n"]
        for promo in promos[:30]:
            if promo["reward_type"] == "case":
                reward = f"case #{promo['case_id']}"
            elif promo["reward_type"] == "stars":
                reward = f"{promo['reward_value']} ⭐"
            else:
                reward = f"{promo['reward_value']} 🍩"
            lines.append(
                f"<code>{promo['code']}</code> — {reward} | "
                f"осталось: <b>{promo['uses_left']}</b>/<b>{promo['max_uses']}</b>"
            )

        await message.answer("\n".join(lines), parse_mode="HTML")

    @dp.message(Command("delpromo"))
    async def cmd_del_promo(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2 or not args[1].strip():
            await message.answer(
                "<b>Удаление промокода</b>\n\n"
                "Использование:\n"
                "<code>/delpromo CODE</code>\n\n"
                "Пример:\n"
                "<code>/delpromo DONUTS100</code>",
                parse_mode="HTML"
            )
            return

        code = args[1].strip().upper()
        deleted = await database.delete_promo_code(code)

        if not deleted:
            await message.answer(f"{E_CROSS} Промокод <code>{code}</code> не найден.", parse_mode="HTML")
            return

        await message.answer(f"{E_CHECK} Промокод <code>{code}</code> удалён.", parse_mode="HTML")

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

    # ──────────────────────────────────────────────────────────────────────────
    # УПРАВЛЕНИЕ ВИДИМОСТЬЮ РАЗДЕЛОВ (/hide и /show)
    # ──────────────────────────────────────────────────────────────────────────

    SECTION_LABELS = {
        "roulette":      "Рулетка",
        "cases":         "Все кейсы",
        "rocket":        "Ракета",
        "limited_gifts": "TG Подарки / Лимитированные подарки",
    }

    @dp.message(Command("hide"))
    async def cmd_hide(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                f"<b>{E_STOP} Скрыть раздел</b>\n\n"
                "Использование:\n"
                "<code>/hide roulette</code> — скрыть рулетку\n"
                "<code>/hide cases</code> — скрыть все кейсы\n"
                "<code>/hide case 3</code> — скрыть кейс с ID 3\n"
                "<code>/hide rocket</code> — скрыть ракету\n"
                "<code>/hide limitedgifts</code> — скрыть TG подарки\n\n"
                "Чтобы вернуть раздел: <code>/show &lt;раздел&gt;</code>",
                parse_mode="HTML"
            )
            return

        section = args[1].lower()

        # Специальная обработка: /hide case <id>
        if section == "case" and len(args) >= 3:
            try:
                case_id = int(args[2])
            except ValueError:
                await message.answer(f"{E_CROSS} ID кейса должен быть числом.", parse_mode="HTML")
                return
            await database.set_feature_flag(f"case_{case_id}", False)
            await message.answer(
                f"{E_CHECK} Кейс <b>#{case_id}</b> скрыт из интерфейса.\n"
                f"Вернуть: <code>/show case {case_id}</code>",
                parse_mode="HTML"
            )
            return

        alias_map = {
            "limitedgifts": "limited_gifts",
            "limited":      "limited_gifts",
            "tgshop":       "limited_gifts",
        }
        section = alias_map.get(section, section)

        if section not in SECTION_LABELS:
            await message.answer(
                f"{E_CROSS} Неизвестный раздел: <b>{section}</b>\n\n"
                "Доступные разделы: roulette, cases, case &lt;id&gt;, rocket, limitedgifts",
                parse_mode="HTML"
            )
            return

        await database.set_feature_flag(section, False)
        label = SECTION_LABELS[section]
        await message.answer(
            f"{E_CHECK} <b>{label}</b> скрыт из интерфейса.\n"
            f"Вернуть: <code>/show {args[1]}</code>",
            parse_mode="HTML"
        )

    @dp.message(Command("show"))
    async def cmd_show(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                f"<b>{E_CHECK} Показать раздел</b>\n\n"
                "Использование:\n"
                "<code>/show roulette</code>\n"
                "<code>/show cases</code>\n"
                "<code>/show case 3</code>\n"
                "<code>/show rocket</code>\n"
                "<code>/show limitedgifts</code>",
                parse_mode="HTML"
            )
            return

        section = args[1].lower()

        # Специальная обработка: /show case <id>
        if section == "case" and len(args) >= 3:
            try:
                case_id = int(args[2])
            except ValueError:
                await message.answer(f"{E_CROSS} ID кейса должен быть числом.", parse_mode="HTML")
                return
            await database.set_feature_flag(f"case_{case_id}", True)
            await message.answer(
                f"{E_CHECK} Кейс <b>#{case_id}</b> снова виден в интерфейсе.",
                parse_mode="HTML"
            )
            return

        alias_map = {
            "limitedgifts": "limited_gifts",
            "limited":      "limited_gifts",
            "tgshop":       "limited_gifts",
        }
        section = alias_map.get(section, section)

        if section not in SECTION_LABELS:
            await message.answer(
                f"{E_CROSS} Неизвестный раздел: <b>{section}</b>",
                parse_mode="HTML"
            )
            return

        await database.set_feature_flag(section, True)
        label = SECTION_LABELS[section]
        await message.answer(
            f"{E_CHECK} <b>{label}</b> снова виден в интерфейсе.",
            parse_mode="HTML"
        )

    @dp.message(Command("featurestatus"))
    async def cmd_feature_status(message: Message):
        """Показывает текущее состояние всех флагов и режима обслуживания."""
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        flags = await database.get_feature_flags()
        maintenance = await database.get_maintenance_mode()

        def flag_icon(v): return E_CHECK if v else E_CROSS

        maintenance_icon = "🔴" if maintenance else "🟢"
        lines = [
            f"<b>📊 Статус интерфейса</b>\n",
            f"{maintenance_icon} Тех. перерыв: <b>{'ВКЛ' if maintenance else 'ВЫКЛ'}</b>\n",
            f"<b>Разделы:</b>",
            f"  {flag_icon(flags.get('roulette', True))}  Рулетка",
            f"  {flag_icon(flags.get('cases', True))}  Все кейсы",
            f"  {flag_icon(flags.get('rocket', True))}  Ракета",
            f"  {flag_icon(flags.get('limited_gifts', True))}  TG Подарки",
        ]

        # Добавляем отдельные кейсы, если есть
        case_flags = {k: v for k, v in flags.items() if k.startswith("case_")}
        if case_flags:
            lines.append("\n<b>Отдельные кейсы:</b>")
            for k, v in sorted(case_flags.items()):
                cid = k.replace("case_", "")
                lines.append(f"  {flag_icon(v)}  Кейс #{cid}")

        await message.answer("\n".join(lines), parse_mode="HTML")

    # ──────────────────────────────────────────────────────────────────────────
    # РЕЖИМ ТЕХНИЧЕСКОГО ОБСЛУЖИВАНИЯ (/maintenance)
    # ──────────────────────────────────────────────────────────────────────────

    @dp.message(Command("maintenance"))
    async def cmd_maintenance(message: Message):
        if message.from_user.id != config.ADMIN_ID:
            await message.answer(f"{E_STOP} У вас нет прав.", parse_mode="HTML")
            return

        args = message.text.split()
        current_mode = await database.get_maintenance_mode()

        if len(args) < 2 or args[1].lower() not in ("on", "off"):
            current = "ВКЛ 🔴" if current_mode else "ВЫКЛ 🟢"
            await message.answer(
                f"<b>🔧 Режим технического обслуживания</b>\n\n"
                f"Текущий статус: <b>{current}</b>\n\n"
                "Использование:\n"
                "<code>/maintenance on</code>  — включить тех. перерыв\n"
                "<code>/maintenance off</code> — выключить тех. перерыв\n\n"
                "<i>При включении пользователи видят экран обслуживания\n"
                "и не могут выполнять никаких действий в приложении.</i>",
                parse_mode="HTML"
            )
            return

        turn_on = args[1].lower() == "on"

        if turn_on and current_mode:
            await message.answer("ℹ️ Тех. перерыв уже включён.", parse_mode="HTML")
            return
        if not turn_on and not current_mode:
            await message.answer("ℹ️ Тех. перерыв уже выключен.", parse_mode="HTML")
            return

        await database.set_maintenance_mode(turn_on)

        if turn_on:
            await message.answer(
                f"🔴 <b>Технический перерыв ВКЛЮЧЁН.</b>\n\n"
                "Пользователи видят экран обслуживания.\n"
                "Выключить: <code>/maintenance off</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"🟢 <b>Технический перерыв ВЫКЛЮЧЕН.</b>\n\n"
                "Приложение снова доступно для всех пользователей.",
                parse_mode="HTML"
            )
