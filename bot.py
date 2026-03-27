# bot.py — точка входа
import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
import database
from handlers import start, admin
from workers import (
    roulette_reminder_worker,
    gift_claim_reminder_worker,
    gift_withdraw_reminder_worker,
    free_case_reminder_worker,
    price_update_worker,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


async def main():
    await database.init_db()

    logging.info("Инициализация обновления цен подарков (API Portals)...")
    config.update_base_gifts_prices()

    # Регистрация хэндлеров
    start.register(dp, bot)
    admin.register(dp, bot)

    await bot.delete_webhook(drop_pending_updates=True)

    # Запуск фоновых задач
    asyncio.create_task(roulette_reminder_worker(bot))
    asyncio.create_task(gift_claim_reminder_worker(bot))
    asyncio.create_task(gift_withdraw_reminder_worker(bot))
    asyncio.create_task(free_case_reminder_worker(bot))
    asyncio.create_task(price_update_worker())

    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())