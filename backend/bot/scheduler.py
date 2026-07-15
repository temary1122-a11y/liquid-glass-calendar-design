"""
APScheduler — reminder job.

Sends ONE reminder at 20:00 MSK the evening before the appointment.
Never sends duplicates (tracks reminder_sent in Booking model).
"""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import ADDRESS, BOT_TOKEN
from database.db import Booking, SessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

_scheduler_bot: Bot | None = None


def _get_scheduler_bot() -> Bot:
    global _scheduler_bot
    if _scheduler_bot is None:
        _scheduler_bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _scheduler_bot


async def send_reminders() -> None:
    """
    Send ONE reminder to each client whose booking is tomorrow,
    IF they haven't already received a reminder.

    Runs at 20:00 MSK daily (cron: 0 17 UTC = 20:00 MSK).
    """
    bot = _get_scheduler_bot()

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    with SessionLocal() as db:
        bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id.isnot(None),
                Booking.status.in_(["pending", "confirmed"]),
                Booking.day_date == tomorrow_str,
                Booking.reminder_sent == 0,  # only unsent reminders
            )
            .all()
        )

        reminders_sent = 0
        for booking in bookings:
            try:
                await bot.send_message(
                    chat_id=booking.user_id,
                    text=(
                        f"🔔 <b>Напоминание о записи</b>\n\n"
                        f"📅 Дата: <b>{booking.day_date}</b>\n"
                        f"🕐 Время: <b>{booking.slot_time}</b>\n"
                        f"📍 Адрес: <b>{ADDRESS}</b>\n\n"
                        f"Чтобы отменить запись: /cancel"
                    ),
                )
                booking.reminder_sent = 1
                reminders_sent += 1
                logger.info(
                    "Reminder sent to user_id=%s for %s %s",
                    booking.user_id, booking.day_date, booking.slot_time,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to send reminder to user_id=%s: %s",
                    booking.user_id, exc,
                )

        if reminders_sent:
            db.commit()

    logger.info("Reminder job done. Sent: %d", reminders_sent)


async def auto_complete_past_bookings() -> None:
    """
    Auto-complete bookings where day_date < today, still pending/confirmed.
    Runs at 3:00 AM daily.
    """
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    with SessionLocal() as db:
        past = (
            db.query(Booking)
            .filter(
                Booking.day_date < today_str,
                Booking.status.in_(["pending", "confirmed"]),
            )
            .all()
        )
        for b in past:
            b.status = "completed"
        db.commit()
        logger.info("Auto-completed %d past bookings", len(past))


def start_scheduler() -> None:
    """Register and start the APScheduler."""
    # Send reminders at 20:00 MSK (17:00 UTC) daily
    scheduler.add_job(
        send_reminders,
        trigger="cron",
        hour=17,  # 20:00 MSK = 17:00 UTC
        minute=0,
        id="reminders",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        auto_complete_past_bookings,
        trigger="cron",
        hour=3,
        minute=0,
        id="auto_complete_bookings",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — reminders at 20:00 MSK, auto-complete at 3 AM")
