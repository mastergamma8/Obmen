# support_bot.py — Точка входа для @SpaceDonutSupportBot
#
# Запускай ОТДЕЛЬНО от основного bot.py:
#   python support_bot.py
#
# Требует в .env:
#   SUPPORT_BOT_TOKEN=<токен @SpaceDonutSupportBot>
#   ADMIN_ID=<твой Telegram ID>   (уже есть в config.py)

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
if not SUPPORT_BOT_TOKEN:
    raise ValueError(
        "SUPPORT_BOT_TOKEN не найден в переменных окружения (.env)!\n"
        "Добавь строку: SUPPORT_BOT_TOKEN=<токен бота поддержки>"
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

bot = Bot(token=SUPPORT_BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


async def main():
    # Импортируем здесь, чтобы bot был уже создан
    from handlers.support import register
    register(dp, bot)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот поддержки @SpaceDonutSupportBot запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
