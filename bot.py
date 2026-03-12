# bot.py
import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import config
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class SendMessage(StatesGroup):
    waiting_for_target = State()
    waiting_for_message = State()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    logging.info(f"Пользователь {user_id} нажал /start")
    
    # Обработка реферальной ссылки (например, /start 123456789)
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
        
        # Если есть реферер, привязываем
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

@dp.message(Command("addgift"))
async def cmd_add_gift(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer(f"⛔ У вас нет прав. Ваш ID: {message.from_user.id}")
        return
    
    args = message.text.split()
    if len(args) != 4:
        await message.answer("Использование: /addgift <ID пользователя> <ID подарка> <Количество>\nПример: /addgift 123456789 2 5")
        return
        
    try:
        user_id = int(args[1])
        gift_id = int(args[2])
        amount = int(args[3])
        
        # Создаем кнопку для перехода в профиль
        profile_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Посмотреть в профиле", web_app=WebAppInfo(url=config.WEBAPP_URL))]
        ])
        
        if gift_id in config.BASE_GIFTS:
            points_to_add = amount * config.BASE_GIFTS[gift_id]['value']
            await database.add_points_to_user(user_id, points_to_add)
            gift_name = config.BASE_GIFTS[gift_id]['name']
            
            await message.answer(f"✅ Успешно!\nПользователю {user_id} начислено {points_to_add} 💎 (за {amount} шт. '{gift_name}').")
            
            # НОВОЕ: Отправляем уведомление самому пользователю с кнопкой
            try:
                await bot.send_message(
                    user_id, 
                    f"🎁 <b>Получен новый подарок!</b>\n<b>{gift_name}</b> ({amount} шт.).\nВам начислено <b>{points_to_add} 🍩</b>!", 
                    parse_mode="HTML",
                    reply_markup=profile_markup
                )
            except Exception as e:
                logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            
            # РЕФЕРАЛЬНАЯ СИСТЕМА: Начисляем 10% пригласившему
            referrer_id = await database.get_referrer(user_id)
            if referrer_id:
                # Берем 10%, минимум 1 балл (чтобы человек точно получил бонус)
                ref_bonus = max(1, int(points_to_add * 0.1))
                await database.add_points_to_user(referrer_id, ref_bonus)
                try:
                    await bot.send_message(referrer_id, f"🥳 Ваш реферал добавил подарок!\nВам начислено <b>{ref_bonus} 💎</b> (10% бонус).", parse_mode="HTML")
                except:
                    pass # Реферер мог заблокировать бота
                    
        elif gift_id in config.MAIN_GIFTS:
            await database.add_gift_to_user(user_id, gift_id, amount)
            gift_name = config.MAIN_GIFTS[gift_id]['name']
            await message.answer(f"✅ Успешно!\nПользователю {user_id} выдан Главный подарок '{gift_name}' ({amount} шт.).")
            
            # НОВОЕ: Отправляем уведомление самому пользователю с кнопкой
            try:
                await bot.send_message(
                    user_id, 
                    f"🎁 <b>Вам отправлен Главный подарок!</b>\nАдминистратор выдал вам <b>{gift_name}</b> ({amount} шт.).\nЗайдите в приложение, чтобы увидеть его в профиле!", 
                    parse_mode="HTML",
                    reply_markup=profile_markup
                )
            except Exception as e:
                logging.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
        
        else:
            await message.answer(f"Подарок с ID {gift_id} не найден в config.py.")

    except ValueError:
        await message.answer("Ошибка: ID и Количество должны быть числами.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("Действие отменено.")

@dp.message(Command("send"))
async def cmd_send(message: types.Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("⛔ У вас нет прав.")
        return
    await message.answer("Кому отправить сообщение? Напишите слово <b>всем</b> или отправьте <b>ID пользователя</b>.\n<i>(Для отмены введите /cancel)</i>", parse_mode="HTML")
    await state.set_state(SendMessage.waiting_for_target)

@dp.message(SendMessage.waiting_for_target)
async def process_send_target(message: types.Message, state: FSMContext):
    text = message.text.lower().strip() if message.text else ""
    if text == "всем":
        await state.update_data(target="all")
    elif text.isdigit():
        await state.update_data(target=int(text))
    else:
        await message.answer("Пожалуйста, напишите 'всем' или числовой ID.")
        return
    await message.answer("Отлично! Теперь отправьте само сообщение. Вы можете прикрепить фото, видео, и использовать любое форматирование текста.")
    await state.set_state(SendMessage.waiting_for_message)

@dp.message(SendMessage.waiting_for_message)
async def process_send_message(message: types.Message, state: FSMContext):
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
        await message.answer(f"✅ Рассылка завершена!\nУспешно доставлено: {success_count}\nОшибок: {fail_count}")
    else:
        try:
            await message.copy_to(chat_id=target)
            await message.answer(f"✅ Сообщение успешно доставлено пользователю {target}!")
        except Exception as e:
            await message.answer(f"❌ Ошибка при отправке.\nДетали: {e}")

async def roulette_reminder_worker(bot: Bot):
    """Фоновая задача для рассылки напоминаний о бесплатной рулетке"""
    while True:
        try:
            now = int(time.time())
            users_to_notify = await database.get_users_to_notify(now)
            
            if users_to_notify:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Крутить рулетку", web_app=WebAppInfo(url=config.WEBAPP_URL))]
                ])
                text = "🎁 Напоминание! Твоя бесплатная прокрутка рулетки снова доступна.\n\nЗаходи в приложение и забирай свои награды!"
                
                for user_id in users_to_notify:
                    try:
                        await bot.send_message(user_id, text, reply_markup=markup)
                        # Обязательно отмечаем, что сообщение отправлено, даже при ошибке,
                        # чтобы бот не пытался отправить его снова в следующем цикле
                        await database.mark_user_notified(user_id)
                        await asyncio.sleep(0.05)  # Защита от флуд-лимитов Telegram
                    except Exception as e:
                        logging.warning(f"Не удалось отправить напоминание {user_id} (возможно заблокировал бота): {e}")
                        await database.mark_user_notified(user_id)
        except Exception as e:
            logging.error(f"Ошибка в воркере напоминаний: {e}")
            
        # Проверяем базу каждые 5 минут (300 секунд)
        await asyncio.sleep(300)

async def main():
    await database.init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем фоновую задачу для напоминаний паралельно с ботом
    asyncio.create_task(roulette_reminder_worker(bot))
    
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())