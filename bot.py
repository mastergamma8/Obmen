# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

import config
import database

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Регистрируем/обновляем пользователя при старте бота (без аватарки, т.к. через бота её получить сложнее, получим из WebApp)
    await database.upsert_user(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "Без имени",
        photo_url=""
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Открыть Mini App", web_app=WebAppInfo(url=config.WEBAPP_URL))]
    ])
    await message.answer("Привет! Нажми на кнопку ниже, чтобы открыть приложение с подарками.", reply_markup=markup)

@dp.message(Command("addgift"))
async def cmd_add_gift(message: types.Message):
    # Команда только для админа: /addgift <tg_id> <gift_id> <amount>
    if message.from_user.id != config.ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) != 4:
        await message.answer("Использование: /addgift <ID пользователя> <ID подарка> <Количество>\nПример: /addgift 123456789 1 2")
        return
        
    try:
        user_id = int(args[1])
        gift_id = int(args[2])
        amount = int(args[3])
        
        if gift_id not in config.GIFTS:
            await message.answer(f"Подарок с ID {gift_id} не найден в config.py.")
            return
            
        await database.add_gift_to_user(user_id, gift_id, amount)
        await message.answer(f"Успешно добавлено {amount} шт. подарка '{config.GIFTS[gift_id]['name']}' пользователю {user_id}.")
    except ValueError:
        await message.answer("Ошибка: ID и Количество должны быть числами.")

async def main():
    await database.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
