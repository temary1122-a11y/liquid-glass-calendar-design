"""
Telegram notification helpers (used outside of bot handlers).
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: str = os.getenv("ADMIN_ID", "")


async def send_telegram_message(
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
) -> bool:
    """
    Send a Telegram message via Bot API (fire-and-forget safe).
    Returns True on success, False on failure.
    """
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram message sent to %s", chat_id)
                return True
            else:
                logger.warning(
                    "Telegram API error %d: %s", resp.status_code, resp.text
                )
                return False
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)
        return False


async def notify_admin(text: str) -> bool:
    """Send a notification to the admin."""
    return await send_telegram_message(ADMIN_ID, text)


async def notify_new_booking(
    client_name: str,
    day_date: str,
    slot_time: str,
    phone: str | None = None,
    username: str | None = None,
) -> None:
    """Notify admin about a new booking."""
    text = (
        f"✅ <b>Новая запись!</b>\n\n"
        f"👤 Имя: {client_name}\n"
        f"📅 Дата: {day_date}\n"
        f"🕐 Время: {slot_time}\n"
        f"📞 Телефон: {phone or '—'}\n"
        f"💬 Telegram: @{username or '—'}"
    )
    await notify_admin(text)


async def notify_booking_cancellation(
    client_name: str,
    day_date: str,
    slot_time: str,
    reason: str | None = None,
    username: str | None = None,
) -> None:
    """Notify admin about a booking cancellation."""
    text = (
        f"🔔 <b>Запись отменена</b>\n\n"
        f"👤 Имя: {client_name}\n"
        f"📅 Дата: {day_date}\n"
        f"🕐 Время: {slot_time}\n"
        f"❌ Причина: {reason or 'Не указана'}\n"
        f"💬 Telegram: @{username or '—'}"
    )
    await notify_admin(text)
