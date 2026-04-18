# ============================================================
# utils/helpers.py — Вспомогательные функции
# ============================================================

import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID, SCHEDULE_CHANNEL_ID

logger = logging.getLogger(__name__)

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля",
    "мая", "июня", "июля", "августа", "сентября",
    "октября", "ноября", "декабря",
]


def format_date_ru(day_date: str) -> str:
    """'2025-06-15' → '15 июня 2025'"""
    try:
        d = datetime.strptime(day_date, "%Y-%m-%d")
        return f"{d.day} {MONTHS_RU[d.month]} {d.year}"
    except Exception:
        return day_date


def booking_text(
    client_name: str,
    phone: str,
    day_date: str,
    slot_time: str,
    booking_id: int | None = None,
) -> str:
    """Форматирует информацию о записи для пользователя."""
    id_line = f"🆔 <code>#{booking_id}</code>\n" if booking_id else ""
    return (
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"{id_line}"
        f"👤 <b>Имя:</b> {client_name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"📅 <b>Дата:</b> {format_date_ru(day_date)}\n"
        f"🕐 <b>Время:</b> {slot_time}\n\n"
        f"💅 Ждём вас! Если нужно отменить — нажмите «❌ Отменить запись»."
    )


def admin_booking_notification(
    client_name: str,
    phone: str,
    day_date: str,
    slot_time: str,
    username: str | None,
    user_id: int,
    booking_id: int,
) -> str:
    """Текст уведомления для администратора о новой записи."""
    uname = f"@{username}" if username else "—"
    return (
        f"🆕 <b>Новая запись!</b>\n\n"
        f"🆔 <code>#{booking_id}</code>\n"
        f"👤 <b>Имя:</b> {client_name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"🔗 <b>Username:</b> {uname}\n"
        f"🪪 <b>User ID:</b> <code>{user_id}</code>\n"
        f"📅 <b>Дата:</b> {format_date_ru(day_date)}\n"
        f"🕐 <b>Время:</b> {slot_time}"
    )


def channel_booking_text(
    client_name: str,
    day_date: str,
    slot_time: str,
    booking_id: int,
) -> str:
    """Текст для публикации в канал расписания."""
    return (
        f"📋 <b>Новая запись в расписании</b>\n\n"
        f"🆔 <code>#{booking_id}</code>\n"
        f"📅 <b>{format_date_ru(day_date)}</b> в <b>{slot_time}</b>\n"
        f"👤 {client_name}"
    )


def client_confirmation_text(day_date: str, slot_time: str) -> str:
    """Текст подтверждения записи для клиента."""
    # Форматируем дату в формат DD.MM
    try:
        from datetime import datetime
        d = datetime.strptime(day_date, "%Y-%m-%d")
        formatted_date = d.strftime("%d.%m")
    except Exception:
        formatted_date = day_date

    # Используем шаблон из config (будет импортирован в handlers/booking.py)
    return (
        f"Записала 💌\n"
        f"📆: {formatted_date}\n"
        f"🟣: {slot_time}\n"
        f"📎Адрес: Тихий переулок, 4\n"
        f"🤩3 этаж, первая дверь справа 🤩"
    )


async def notify_admin(bot: Bot, text: str) -> None:
    """Отправляет сообщение администратору."""
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления администратору: {e}")


async def post_to_schedule_channel(bot: Bot, text: str) -> None:
    """Публикует сообщение в канал расписания."""
    try:
        await bot.send_message(
            chat_id=SCHEDULE_CHANNEL_ID, text=text, parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка публикации в канал расписания: {e}")


async def check_subscription(bot: Bot, user_id: int, channel_id: str) -> bool:
    """
    Проверяет, подписан ли пользователь на канал.
    Использует getChatMember API.
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки для {user_id}: {e}")
        # Если канал не найден или бот не является участником — разрешаем доступ
        return True


async def safe_answer(callback: CallbackQuery, text: str, **kwargs) -> None:
    """Безопасный ответ на callback с удалением предупреждения."""
    try:
        await callback.answer()
    except Exception:
        pass
    try:
        await callback.message.edit_text(text, **kwargs)
    except Exception:
        await callback.message.answer(text, **kwargs)
