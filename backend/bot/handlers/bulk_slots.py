"""
Bulk slot creation handler — /bulk command (admin only).

Format:
  /bulk <text>
  
  where <text> can be:
    "22.07 13:30; 14:00; 15:00"
    "22.07\n13:30\n14:00\n15:00"
    "22.07 13:30, 14:00; 23.07 10:00, 11:00"

Security: admin only check via from_user.id == ADMIN_ID_INT.
"""

import asyncio
import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from config import ADMIN_ID_INT
from database.db import SessionLocal, TimeSlot, WorkDay
from services.bulk_parser import parse_bulk

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "📋 <b>Массовое добавление слотов</b>\n\n"
    "Используйте команду /bulk с указанием дат и времени:\n\n"
    "<b>Формат:</b>\n"
    "<code>/bulk 22.07 13:30; 14:00; 15:00</code>\n\n"
    "<b>Поддерживаемые форматы:</b>\n"
    "• <code>ДД.ММ ЧЧ:ММ; ЧЧ:ММ</code> — одна дата + слоты через ;\n"
    "• <code>ДД.ММ ЧЧ:ММ, ЧЧ:ММ</code> — разделитель запятая\n"
    "• Каждая новая строка = новая дата\n"
    "• <code>31.0711:00</code> — слипшаяся строка (авторазбор)\n"
    "• <code>22 июля 13:00</code> — русские названия месяцев\n\n"
    "<b>Примеры:</b>\n"
    "<code>/bulk 22.07 10:00; 11:00; 12:00</code>\n"
    "<code>/bulk 22.07 10:00, 11:00, 12:00\n23.07 14:00; 15:00</code>"
)


@router.message(Command("bulk"), F.from_user.id == ADMIN_ID_INT)
async def cmd_bulk(message: types.Message) -> None:
    """Handle /bulk command for mass slot creation."""
    text = message.text.strip()

    # If no argument (just "/bulk"), show help
    if text.lower() == "/bulk" or text.lower().startswith("/bulk@"):
        # Check if there's text after the command
        parts = text.split(None, 1)
        if len(parts) < 2:
            await message.answer(HELP_TEXT, parse_mode="HTML")
            return

    admin_id = message.from_user.id
    logger.info("[bulk] Admin %d triggered /bulk", admin_id)

    # Parse the text (remove "/bulk" prefix)
    cmd_prefix = text.split(None, 1)[0]  # "/bulk" or "/bulk@botname"
    raw = text[len(cmd_prefix):].strip()

    if not raw:
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    logger.info("[bulk] Raw input (%d chars): %s", len(raw), raw[:120])

    # Status message
    status_msg = await message.reply(
        "📋 <b>Разбираю слоты...</b>\n\n<code>[▰▱▱]</code>",
        parse_mode="HTML",
    )

    # Parse
    pairs = parse_bulk(raw)
    logger.info("[bulk] Parsed %d slot pairs from input", len(pairs))

    if not pairs:
        logger.warning("[bulk] No valid slot pairs found in input")
        await status_msg.edit_text(
            "❌ <b>Не удалось распознать слоты.</b>\n\n"
            "Проверьте формат:\n"
            "<code>/bulk 22.07 13:30; 14:00; 15:00</code>",
            parse_mode="HTML",
        )
        return

    await status_msg.edit_text(
        f"📋 <b>Найдено {len(pairs)} слотов</b>\n\n"
        f"<code>[▰▰▱]</code>\n\n"
        f"<i>Добавляю...</i>",
        parse_mode="HTML",
    )

    # Add to DB
    added = 0
    skipped = 0
    errors = 0
    new_days = 0

    db = SessionLocal()
    try:
        # Group by date for efficiency
        from collections import defaultdict
        by_date = defaultdict(list)
        for date_str, time_str in pairs:
            by_date[date_str].append(time_str)

        logger.info("[bulk] Processing %d dates: %s", len(by_date), list(by_date.keys()))

        for date_str, times in by_date.items():
            # Ensure WorkDay exists
            work_day = db.query(WorkDay).filter(WorkDay.day_date == date_str).first()
            if not work_day:
                work_day = WorkDay(day_date=date_str, is_closed=0)
                db.add(work_day)
                db.flush()
                new_days += 1
                logger.info("[bulk] Created new WorkDay: %s", date_str)

            for time_str in times:
                # Check if slot already exists
                existing = db.query(TimeSlot).filter(
                    TimeSlot.day_date == date_str,
                    TimeSlot.slot_time == time_str,
                ).first()
                if existing:
                    skipped += 1
                    logger.debug("[bulk] Slot already exists: %s %s", date_str, time_str)
                    continue

                try:
                    slot = TimeSlot(day_date=date_str, slot_time=time_str, is_booked=0)
                    db.add(slot)
                    added += 1
                    logger.debug("[bulk] Added slot: %s %s", date_str, time_str)
                except Exception as exc:
                    logger.error("[bulk] Failed to add slot %s %s: %s", date_str, time_str, exc)
                    errors += 1

        db.commit()
        logger.info("[bulk] Committed: +%d slots, %d skipped, %d new days, %d errors",
                     added, skipped, new_days, errors)
    except Exception as exc:
        db.rollback()
        logger.exception("[bulk] DB transaction failed: %s", exc)
        await status_msg.edit_text(
            f"❌ <b>Ошибка при добавлении:</b>\n{exc}",
            parse_mode="HTML",
        )
        return
    finally:
        db.close()

    # Build result message
    result_parts = [f"✅ <b>Готово!</b>\n"]
    if added:
        result_parts.append(f"➕ Добавлено: <b>{added}</b>")
    if skipped:
        result_parts.append(f"⏭️ Пропущено (уже есть): <b>{skipped}</b>")
    if new_days:
        result_parts.append(f"📅 Новых дней: <b>{new_days}</b>")
    if errors:
        result_parts.append(f"⚠️ Ошибок: <b>{errors}</b>")

    result_parts.append(f"\n📋 <i>Всего обработано: {len(pairs)} слотов</i>")

    await status_msg.edit_text("\n".join(result_parts), parse_mode="HTML")


@router.message(Command("bulk"))
async def cmd_bulk_denied(message: types.Message) -> None:
    """Non-admin users get silent ignore."""
    # Don't leak that /bulk exists to non-admins
    pass
