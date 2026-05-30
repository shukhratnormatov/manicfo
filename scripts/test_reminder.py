"""
Одноразовый скрипт: вызывает send_daily_reminders вручную.
DB замокирована — реальные запросы к Supabase не нужны.
Telegram API — настоящий.

Запуск:
    ~/.local/bin/uv run python scripts/test_reminder.py
"""
import asyncio
import os

# Env из data.env.md (SUPABASE_URL недоступен, поэтому ставим заглушку для импорта)
os.environ.setdefault("BOT_TOKEN", "8780141891:AAH-GV1zusxwM1QFLXPf6bwkARjbhL7VeT0")
os.environ.setdefault("SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("OWNER_TG_ID", "36566562")

from aiogram import Bot
from bot.services.scheduler import send_daily_reminders


class MockDb:
    """Возвращает только owner для тестового прогона."""
    async def get_all_active_users(self):
        return [int(os.environ["OWNER_TG_ID"])]


async def main():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    bot = Bot(token=os.environ["BOT_TOKEN"])
    try:
        print(f"Sending reminder to user_id={os.environ['OWNER_TG_ID']}...")
        await send_daily_reminders(bot, MockDb())
        print("Done — check Telegram.")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
