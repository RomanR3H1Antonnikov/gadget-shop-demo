"""
main.py
-------
Точка входа бота GadgetPro.
Инициализирует БД, регистрирует роутеры и запускает polling.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.database.models import init_db
from bot.handlers import catalog, orders, ai_consultant, admin, my_orders, fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Инициализируем БД при старте
    await init_db()
    logger.info("БД инициализирована.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры в порядке приоритета
    dp.include_router(catalog.router)
    dp.include_router(orders.router)
    dp.include_router(ai_consultant.router)
    dp.include_router(admin.router)
    dp.include_router(my_orders.router)
    dp.include_router(fallback.router)  # всегда последним

    logger.info("Бот запущен.")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
