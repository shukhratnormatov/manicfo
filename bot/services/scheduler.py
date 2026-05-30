import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=pytz.utc)


async def send_daily_reminders(bot, db) -> None:
    """Отправляет напоминание всем активным пользователям (owner + beta)."""
    users = await db.get_all_active_users()
    text = (
        "👋 Привет!\n\n"
        "Не забудь записать свои расходы и доходы за сегодня.\n"
        "Это позволит держать актуальную статистику и следить за целями.\n\n"
        "Просто напиши: «потратил 50к на продукты» 💰"
    )
    sent = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception:
            pass  # пользователь заблокировал бота — пропускаем молча
    logger.info("Daily reminders sent: %d / %d", sent, len(users))


def setup_scheduler(bot, db) -> AsyncIOScheduler:
    """Регистрирует задачу ежедневного напоминания и возвращает планировщик.

    10:00 по Ташкенту (UTC+5) = 05:00 UTC.
    """
    scheduler.add_job(
        send_daily_reminders,
        trigger=CronTrigger(hour=5, minute=0, timezone=pytz.utc),
        args=[bot, db],
        id="daily_reminder",
        replace_existing=True,
    )
    logger.info("Daily reminder job registered (05:00 UTC = 10:00 Tashkent).")
    return scheduler
