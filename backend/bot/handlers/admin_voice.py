"""
Admin voice + text command handler — ONLY for the admin.

Handles:
  - Voice messages → Groq Whisper transcription → Groq LLM extraction → DB command execution
  - Text voice commands → direct extraction → DB command execution
  - Bulk slot format auto-detection (DD.MM HH:MM patterns)
  - Common button delegation (so admin buttons don't break)
  - Fallback: regex extraction when Groq API is unavailable
  - Live progress steps with message editing for smooth UX
"""

import asyncio
import logging
import os
import re
import tempfile

from aiogram import Bot, F, Router, types
from aiogram.filters import Command

from config import ADMIN_ID_INT, GROQ_API_KEY
from services.admin_command import execute_command
from services.bulk_parser import parse_bulk
from services.groq_client import extract_command, transcribe_voice
from database.db import SessionLocal, TimeSlot, WorkDay

logger = logging.getLogger(__name__)

router = Router()


# ── Progress steps helper ──────────────────────────────

async def _edit_progress(msg: types.Message, step: str, total_steps: int,
                          current: int, detail: str = "") -> None:
    bar = "▰" * current + "▱" * (total_steps - current)
    text = f"{step}\n\n<code>[{bar}]</code>"
    if detail:
        text += f"\n<i>{detail}</i>"
    await msg.edit_text(text, parse_mode="HTML")


# ── /vc ────────────────────────────────────────────────

@router.message(Command("vc"), F.from_user.id == ADMIN_ID_INT)
async def cmd_vc_help(message: types.Message) -> None:
    await message.answer(
        "🎤 <b>Голосовые команды для админа</b>\n\n"
        "Просто отправьте голосовое сообщение или текст с командой:\n\n"
        "<b>Создать запись:</b>\n"
        "• «Запиши Алину на 12:00 21 числа»\n"
        "• «Запиши Свету на завтра в 15:00»\n\n"
        "<b>Отменить запись:</b>\n"
        "• «Отмени запись Алины»\n"
        "• «Удали запись на 21.07 в 12:00»\n\n"
        "<b>Посмотреть записи:</b>\n"
        "• «Кто записан 21 числа?»\n"
        "• «Покажи записи на сегодня»\n\n"
        "<b>Управление днями:</b>\n"
        "• «Выходной 21 числа»\n"
        "• «Открой 21 июля»\n\n"
        f"<i>Groq API: {'✅ подключен' if GROQ_API_KEY else '❌ не настроен (текстовый fallback)'}</i>",
        parse_mode="HTML",
    )


# ── Voice handler ─────────────────────────────────────

@router.message(F.voice, F.from_user.id == ADMIN_ID_INT)
async def handle_admin_voice(message: types.Message, bot: Bot) -> None:
    """Admin voice → 4 progress steps → execute → reply."""
    total_steps = 4
    admin_id = message.from_user.id
    logger.info("[voice] Admin %d sent voice msg (msg_id=%d)", admin_id, message.message_id)

    status_msg = await message.reply(
        f"🎤 <b>Скачиваю голосовое...</b>\n\n"
        f"<code>[▰▱▱▱]</code>",
        parse_mode="HTML",
    )

    voice = message.voice
    file_info = await bot.get_file(voice.file_id)
    tmp_path = os.path.join(
        tempfile.gettempdir(),
        f"liquid_glass_voice_{message.message_id}.oga",
    )
    await bot.download_file(file_info.file_path, tmp_path)
    logger.info("[voice] Downloaded: %s (%d bytes)", tmp_path, voice.file_size or 0)

    await _edit_progress(status_msg, "🔊 <b>Расшифровываю речь...</b>", total_steps, 2,
                          detail=f"Размер: {voice.file_size or '?'} байт")
    transcribed = await transcribe_voice(tmp_path)

    try:
        os.remove(tmp_path)
    except OSError:
        pass

    if not transcribed:
        logger.warning("[voice] Transcription empty for msg_id=%d", message.message_id)
        await status_msg.edit_text(
            "❌ <b>Не удалось распознать голос.</b>\n\n"
            "Попробуйте ещё раз или напишите команду текстом.\n"
            "Пример: <i>Запиши Алину на 12:00 21 числа</i>",
            parse_mode="HTML",
        )
        return

    await _edit_progress(
        status_msg, "🔍 <b>Анализирую команду...</b>", total_steps, 3,
        detail=f"«{transcribed[:60]}{'...' if len(transcribed) > 60 else ''}»",
    )
    cmd = await extract_command(transcribed)
    logger.info("[voice] Extracted: action=%s name=%s date=%s time=%s",
                cmd.get("action"), cmd.get("client_name"), cmd.get("date"), cmd.get("time"))

    action_labels = {
        "book": "✏️ Создаю запись...",
        "cancel": "🗑️ Отменяю запись...",
        "check": "📋 Смотрю записи...",
        "set_day_off": "📴 Закрываю день...",
        "set_day_on": "📅 Открываю день...",
        "unknown": "🤔 Обрабатываю...",
    }
    action_label = action_labels.get(cmd.get("action", "unknown"), "⚙️ Выполняю...")
    await _edit_progress(status_msg, f"{action_label}", total_steps, 4)
    result = await execute_command(cmd)

    conf_emoji = {"high": "🎯", "medium": "👍", "low": "🤔"}.get(
        cmd.get("confidence", "medium"), "👍")
    await status_msg.edit_text(
        f"{result}\n\n"
        f"<i>🎤 «{transcribed}» {conf_emoji}</i>",
        parse_mode="HTML",
    )


# ── Bulk format detection ──────────────────────────────

# Pattern: line starts with DD.MM or DD.MM (glued) followed by time(s)
_BULK_LINE_RE = re.compile(r'\d{1,2}\.\d{1,2}')

def _is_bulk_format(text: str) -> bool:
    """Detect if text looks like bulk slot format (not a voice command)."""
    # Must have at least 2 date-like patterns (DD.MM) AND time patterns (HH:MM)
    date_matches = _BULK_LINE_RE.findall(text)
    time_matches = re.findall(r'\d{1,2}:\d{2}', text)
    return len(date_matches) >= 2 and len(time_matches) >= 1


# ── /bulk command ─────────────────────────────────────

_BULK_HELP = (
    "📋 <b>Массовое добавление слотов</b>\n\n"
    "Просто отправьте даты и время в формате:\n\n"
    "<code>22.07 13:30;\n"
    "24.07 13:30;\n"
    "28.07 13:30; 16:00\n"
    "29.07 11:00; 13:30; 16:00</code>\n\n"
    "• Разделители: <code>;</code> <code>,</code> или новая строка\n"
    "• <code>31.0711:00</code> — слипшаяся дата+время\n"
    "• <code>22 июля 13:00</code> — русские месяцы\n"
    "• Уже существующие слоты пропускаются"
)


@router.message(Command("bulk"), F.from_user.id == ADMIN_ID_INT)
async def cmd_bulk(message: types.Message) -> None:
    """Handle /bulk command."""
    text = message.text.strip()
    parts = text.split(None, 1)

    if len(parts) < 2:
        await message.answer(_BULK_HELP, parse_mode="HTML")
        return

    raw = parts[1].strip()
    logger.info("[bulk] Admin triggered /bulk with %d chars", len(raw))
    await _process_bulk(message, raw)


@router.message(Command("bulk"))
async def cmd_bulk_denied(message: types.Message) -> None:
    pass  # Silent ignore for non-admins


async def _process_bulk(message: types.Message, raw: str) -> None:
    """Parse and insert bulk slots, reply with result."""
    status_msg = await message.reply(
        "📋 <b>Разбираю слоты...</b>\n\n<code>[▰▱▱]</code>",
        parse_mode="HTML",
    )

    pairs = parse_bulk(raw)
    logger.info("[bulk] Parsed %d pairs from %d chars", len(pairs), len(raw))

    if not pairs:
        logger.warning("[bulk] No valid pairs found")
        await status_msg.edit_text(
            "❌ <b>Не удалось распознать слоты.</b>\n\n"
            "Проверьте формат:\n"
            "<code>22.07 13:30;\n24.07 13:30;</code>",
            parse_mode="HTML",
        )
        return

    await status_msg.edit_text(
        f"📋 <b>Найдено {len(pairs)} слотов</b>\n\n"
        f"<code>[▰▰▱]</code>\n\n<i>Добавляю...</i>",
        parse_mode="HTML",
    )

    from collections import defaultdict
    added, skipped, errors, new_days = 0, 0, 0, 0

    db = SessionLocal()
    try:
        by_date = defaultdict(list)
        for date_str, time_str in pairs:
            by_date[date_str].append(time_str)

        logger.info("[bulk] Processing %d dates: %s", len(by_date), list(by_date.keys()))

        for date_str, times in by_date.items():
            wd = db.query(WorkDay).filter(WorkDay.day_date == date_str).first()
            if not wd:
                wd = WorkDay(day_date=date_str, is_closed=0)
                db.add(wd)
                db.flush()
                new_days += 1
                logger.info("[bulk] New WorkDay: %s", date_str)

            for t in times:
                ex = db.query(TimeSlot).filter(
                    TimeSlot.day_date == date_str, TimeSlot.slot_time == t
                ).first()
                if ex:
                    skipped += 1
                    continue
                try:
                    db.add(TimeSlot(day_date=date_str, slot_time=t, is_booked=0))
                    added += 1
                except Exception as exc:
                    logger.error("[bulk] Failed %s %s: %s", date_str, t, exc)
                    errors += 1

        db.commit()
        logger.info("[bulk] Done: +%d/%d skip/%d days/%d err", added, skipped, new_days, errors)
    except Exception as exc:
        db.rollback()
        logger.exception("[bulk] Transaction failed: %s", exc)
        await status_msg.edit_text(f"❌ <b>Ошибка:</b>\n{exc}", parse_mode="HTML")
        return
    finally:
        db.close()

    parts = [f"✅ <b>Готово!</b>\n"]
    if added:
        parts.append(f"➕ Добавлено: <b>{added}</b>")
    if skipped:
        parts.append(f"⏭️ Пропущено: <b>{skipped}</b>")
    if new_days:
        parts.append(f"📅 Новых дней: <b>{new_days}</b>")
    if errors:
        parts.append(f"⚠️ Ошибок: <b>{errors}</b>")
    parts.append(f"\n📋 <i>Обработано: {len(pairs)} слотов</i>")
    await status_msg.edit_text("\n".join(parts), parse_mode="HTML")


# ── Text command handler (ALL admin text) ─────────────

@router.message(
    F.text,
    F.from_user.id == ADMIN_ID_INT,
    ~F.text.startswith("/"),
)
async def handle_admin_text(message: types.Message) -> None:
    """
    Central admin text dispatcher.
    1. Button text → delegate to common_router methods
    2. Bulk format → auto-process as mass slot creation
    3. Voice command text → extract + execute
    4. Otherwise → silent ignore
    """
    text = message.text.strip()
    if not text:
        return

    admin_id = message.from_user.id

    # 1. Common button text — forward to common handler
    if text in ("📅 Записаться", "📋 Моя запись", "❌ Отменить запись", "❓ Помощь"):
        logger.info("[admin_text] Admin %d pressed button: %s", admin_id, text[:30])
        from bot.handlers.common import btn_book, btn_my_booking, btn_cancel_booking, btn_help
        button_map = {
            "📅 Записаться": btn_book,
            "📋 Моя запись": btn_my_booking,
            "❌ Отменить запись": btn_cancel_booking,
            "❓ Помощь": btn_help,
        }
        handler = button_map.get(text)
        if handler:
            # btn_cancel_booking needs state parameter (FSMContext)
            if text == "❌ Отменить запись":
                from aiogram.fsm.context import FSMContext
                from aiogram.fsm.storage.memory import MemoryStorage
                # aiogram provides FSMContext via dependency injection normally,
                # but here we call directly. The handler reads user_id from message
                # and starts the cancel flow. It uses state.update_data/set_state.
                # We'll pass a dummy state since btn_cancel_booking just starts a new flow.
                state = FSMContext(storage=MemoryStorage(), key=f"user:{admin_id}")
                await handler(message, state)
            else:
                await handler(message)
        return

    # 2. Bulk format auto-detection
    if _is_bulk_format(text):
        logger.info("[admin_text] Auto-detected bulk format from admin %d", admin_id)
        await _process_bulk(message, text)
        return

    # 3. Voice command text
    cmd_indicators = [
        "запиш", "отмен", "удал", "покаж", "посмотр",
        "кто", "статус", "выходной", "открой", "закрой",
        "добавь слот", "добавь день",
    ]
    if not any(ind in text.lower() for ind in cmd_indicators):
        return  # Nothing matched

    logger.info("[admin_text] Voice command from admin %d: %s", admin_id, text[:100])

    status_msg = await message.reply(
        "💬 <b>Обрабатываю...</b>\n\n<code>[▰▰▱▱]</code>",
        parse_mode="HTML",
    )

    await _edit_progress(status_msg, "🔍 <b>Анализирую...</b>", 4, 3,
                          detail=f"«{text[:60]}{'...' if len(text) > 60 else ''}»")
    cmd = await extract_command(text)
    logger.info("[admin_text] Extracted: action=%s name=%s date=%s time=%s",
                cmd.get("action"), cmd.get("client_name"), cmd.get("date"), cmd.get("time"))

    action_labels = {
        "book": "✏️ Создаю запись...",
        "cancel": "🗑️ Отменяю...",
        "check": "📋 Смотрю...",
        "set_day_off": "📴 Закрываю день...",
        "set_day_on": "📅 Открываю день...",
        "unknown": "🤔 Обрабатываю...",
    }
    action_label = action_labels.get(cmd.get("action", "unknown"), "⚙️ Выполняю...")
    await _edit_progress(status_msg, action_label, 4, 4)
    result = await execute_command(cmd)

    conf_emoji = {"high": "🎯", "medium": "👍", "low": "🤔"}.get(
        cmd.get("confidence", "medium"), "👍")
    await status_msg.edit_text(
        f"{result}\n\n"
        f"<i>💬 «{text[:100]}» {conf_emoji}</i>",
        parse_mode="HTML",
    )
