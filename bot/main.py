import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.middlewares.auth import AuthMiddleware
from bot.handlers import start, transactions, goals, stats, rates, subscriptions, admin, edit

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="stats",   description="📊 Статистика месяца"),
        BotCommand(command="goals",   description="🎯 Цели накопления"),
        BotCommand(command="history", description="📋 Последние транзакции"),
        BotCommand(command="subs",    description="📱 Подписки"),
        BotCommand(command="rates",   description="💱 Курс валют"),
        BotCommand(command="week",    description="📅 Итоги недели"),
        BotCommand(command="help",    description="❓ Помощь"),
    ])
    logger.info("Bot commands registered.")


async def main():
    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = Dispatcher(storage=MemoryStorage())

    dp.startup.register(on_startup)

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(edit.router)      # FSM редактирования — до transactions
    dp.include_router(goals.router)
    dp.include_router(stats.router)
    dp.include_router(rates.router)
    dp.include_router(subscriptions.router)
    dp.include_router(transactions.router)

    logger.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
