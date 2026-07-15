"""Bulk slot command — /bulk handler for admin mass-add of time slots."""
import logging
import asyncio

from aiogram import F, Router, types
from aiogram.filters import Command

from config import ADMIN_ID_INT
from database.db import SessionLocal
from services.bulk_parser import parse_bulk_slots_and_execute

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("bulk"), F.from_user.id == ADMIN_ID_INT)
async def cmd_bulk_help(message: types.Message) -> None:
    """Show bulk command usage."""
    await message.answer(
        "📋 <b>Массовое добавление окон</b>\n\n"
        "Отправьте даты и время в формате:\n\n"
        "<code>22.07 13:30;\n"
        "24.07 13:30;\n"
        "28.07 13:30; 16:00\n"
        "29.07 11:00; 13:30; 16:00</code>\n\n"
        "• Разделители: <code>;</code> или <code>,</code> или новая строка\n"
        "• Даже если дата слиплась со временем — пойму: <code>31.0711:00</code>\n"
        "• Уже существующие слоты пропускаются\n\n"
        "<i>Отправьте <b>следующим сообщением</b> ваш список окон.</i>",
        parse_mode="HTML",
    )


@router.message(F.text, F.from_user.id == ADMIN_ID_INT)
async def handle_bulk_text(message: types.Message) -> None:
    """
    Intercept admin text — check if it looks like bulk slot format.
    Bulk format: contains date patterns like "22.07" or "1.07"
    Must NOT look like a voice command (those are handled by admin_voice router).
    """
    text = message.text.strip()
    if not text:
        return

    import re

    # Detect bulk format: has at least 2 date+time patterns
    date_time_pairs = re.findall(r"\d{1,2}\s*[\.\s]\s*\d{1,2}.*?\d{1,2}:\d{2}", text)
    if len(date_time_pairs) < 2:
        return  # not bulk format, let other handlers process

    logger.info("Bulk slot command detected from admin %s", message.from_user.id)

    status_msg = await message.reply("⚙️ <b>Анализирую окна...</b>", parse_mode="HTML")

    # Execute in thread to not block
    def _do():
        with SessionLocal() as db:
            return parse_bulk_slots_and_execute(text, db)

    try:
        result = await asyncio.to_thread(_do)
        await status_msg.edit_text(result, parse_mode="HTML")
    except Exception as exc:
        logger.error("Bulk slot failed: %s", exc, exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Ошибка при добавлении окон</b>\n\n<code>{str(exc)[:200]}</code>",
            parse_mode="HTML",
        )
