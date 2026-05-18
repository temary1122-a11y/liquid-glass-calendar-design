"""
APScheduler — reminder job.

Runs every hour, sends reminders to users whose appointment is tomorrow.
"""

import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.db import Booking, SessionLocal

logger = logging.getLogger(__name__)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADDRESS: str = "Тихий переулок, 4"

# Singleton scheduler
scheduler = AsyncIOScheduler()


async def send_reminders() -> None:
    """
    Send appointment reminders for bookings scheduled for tomorrow.
    Called every hour by APScheduler.
    """
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    with SessionLocal() as db:
        bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id.isnot(None),
                Booking.status.in_(["pending", "confirmed"]),
            )
            .all()
        )

        reminders_sent = 0
        for booking in bookings:
            slot = booking.slot
            if not slot:
                continue
            work_day = slot.work_day
            if not work_day:
                continue

            if work_day.day_date != tomorrow_str:
                continue

            try:
                await bot.send_message(
                    chat_id=booking.user_id,
                    text=(
                        f"🔔 <b>Напоминание о записи</b>\n\n"
                        f"📅 Дата: <b>{work_day.day_date}</b>\n"
                        f"🕐 Время: <b>{slot.time}</b>\n"
                        f"📍 Адрес: <b>{ADDRESS}</b>\n\n"
                        f"Чтобы отменить запись: /cancel"
                    ),
                )
                reminders_sent += 1
                logger.info(
                    "Reminder sent to user_id=%s for %s %s",
                    booking.user_id,
                    work_day.day_date,
                    slot.time,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to send reminder to user_id=%s: %s",
                    booking.user_id,
                    exc,
                )

    await bot.session.close()
    logger.info("Reminder job done. Sent: %d", reminders_sent)


async def auto_complete_past_bookings() -> None:
    """
    Automatically complete past bookings (day_date < today) that are still pending or confirmed.
    Runs once a day.
    """
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    with SessionLocal() as db:
        past_bookings = (
            db.query(Booking)
            .filter(
                Booking.day_date < today_str,
                Booking.status.in_(["pending", "confirmed"])
            )
            .all()
        )
        for b in past_bookings:
            b.status = "completed"
        db.commit()
        logger.info("Auto-completed %d past bookings", len(past_bookings))


def start_scheduler() -> None:
    """Register and start the APScheduler."""
    scheduler.add_job(
        send_reminders,
        trigger="interval",
        hours=1,
        id="reminders",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        auto_complete_past_bookings,
        trigger="cron",
        hour=3,  # 3 AM daily
        minute=0,
        id="auto_complete_bookings",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — reminder job runs every hour, auto-complete at 3 AM daily")
