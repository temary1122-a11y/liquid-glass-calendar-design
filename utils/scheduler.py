# ============================================================
# utils/scheduler.py — APScheduler: напоминания о записях
# ============================================================

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from aiogram import Bot

logger = logging.getLogger(__name__)

# Глобальный экземпляр планировщика
scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    timezone="Europe/Moscow",
)


async def _send_reminder(bot: Bot, user_id: int, slot_time: str) -> None:
    """Функция-задача: отправляет напоминание пользователю."""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"⏰ <b>Напоминание о записи!</b>\n\n"
                f"Напоминаем, что вы записаны на наращивание ресниц "
                f"<b>завтра в {slot_time}</b>.\n\n"
                f"Ждём вас! 💖✨"
            ),
            parse_mode="HTML",
        )
        logger.info(f"Напоминание отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания {user_id}: {e}")


def schedule_reminder(bot: Bot, booking_id: int, user_id: int, day_date: str, slot_time: str) -> bool:
    """
    Планирует напоминание за 24 часа до записи.
    Возвращает True если задача запланирована, False если запись < 24ч.
    """
    try:
        dt_visit = datetime.strptime(f"{day_date} {slot_time}", "%Y-%m-%d %H:%M")
        dt_remind = dt_visit - timedelta(hours=24)

        now = datetime.now()
        if dt_remind <= now:
            logger.info(f"Запись #{booking_id}: напоминание не создаётся (< 24ч до визита)")
            return False

        job_id = f"reminder_{booking_id}"
        scheduler.add_job(
            _send_reminder,
            trigger="date",
            run_date=dt_remind,
            args=[bot, user_id, slot_time],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,  # допустимая задержка 1 час
        )
        logger.info(f"Напоминание #{booking_id} запланировано на {dt_remind}")
        return True
    except Exception as e:
        logger.error(f"Ошибка планирования напоминания: {e}")
        return False


def cancel_reminder(booking_id: int) -> None:
    """Удаляет задачу напоминания при отмене записи."""
    job_id = f"reminder_{booking_id}"
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Напоминание {job_id} удалено")
    except Exception as e:
        logger.error(f"Ошибка удаления напоминания {job_id}: {e}")


def restore_reminders_from_db(bot: Bot, bookings: list) -> None:
    """
    Восстанавливает задачи напоминаний из БД при старте бота.
    bookings — список записей из get_all_future_bookings().
    """
    restored = 0
    for b in bookings:
        scheduled = schedule_reminder(
            bot=bot,
            booking_id=b["id"],
            user_id=b["user_id"],
            day_date=b["day_date"],
            slot_time=b["slot_time"],
        )
        if scheduled:
            restored += 1
    logger.info(f"Восстановлено {restored} напоминаний из БД.")
