# bot.py — инстанс бота и регистрация хэндлеров
#
# В продакшене (Railway) бот работает через webhook внутри FastAPI (main.py).
# При локальной разработке можно запустить напрямую: python bot.py — тогда
# используется long polling.

import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
from handlers import start, admin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инстансы создаются на уровне модуля — импортируются из main.py для webhook-режима.
bot = Bot(token=config.BOT_TOKEN)
dp  = Dispatcher()


def setup_handlers():
    """Регистрирует хэндлеры на диспетчере. Вызывается один раз при старте."""
    start.register(dp, bot)
    admin.register(dp, bot)


# ── Локальный запуск (long polling) ───────────────────────────────────────────

async def _run_polling():
    """Только для локальной разработки. В продакшене используется webhook."""
    import database
    from db.db_async import init_pool, close_pool
    from db.db_core import DB_NAME
    from handlers.workers import (
        roulette_reminder_worker,
        gift_claim_reminder_worker,
        gift_withdraw_reminder_worker,
        free_case_reminder_worker,
    )

    await init_pool(DB_NAME, min_size=2, max_size=10)
    try:
        await database.init_db()
        await database.init_settings_table()

        setup_handlers()

        await bot.delete_webhook(drop_pending_updates=True)
        try:
            await bot.get_updates(offset=0, timeout=0)
        except Exception:
            pass
        await asyncio.sleep(3)

        asyncio.create_task(roulette_reminder_worker(bot))
        asyncio.create_task(gift_claim_reminder_worker(bot))
        asyncio.create_task(gift_withdraw_reminder_worker(bot))
        asyncio.create_task(free_case_reminder_worker(bot))

        logging.info("Бот запущен! (polling-режим)")
        await dp.start_polling(bot)
    finally:
        await close_pool()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(_run_polling())
