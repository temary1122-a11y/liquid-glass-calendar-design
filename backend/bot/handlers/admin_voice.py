"""
Admin voice command handler — ONLY for the admin.

Handles:
  - Voice messages → Groq Whisper transcription → Groq LLM extraction → DB command execution
  - Text commands (same format) → direct extraction → DB command execution
  - Fallback: regex extraction when Groq API is unavailable
  - Live progress steps with message editing for smooth UX

Security:
  - ALL handlers check `message.from_user.id == ADMIN_ID_INT`
  - Non-admin users get a silent ignore (no error, no info leak)

Examples of supported commands (voice or text):
  «Запиши Алину на 12:00 21 числа»
  «Отмени запись Алины»
  «Кто записан 21 числа?»
  «Выходной 21 числа»
"""

import logging
import os
import tempfile

from aiogram import Bot, F, Router, types
from aiogram.filters import Command

from config import ADMIN_ID_INT, GROQ_API_KEY
from services.admin_command import execute_command
from services.groq_client import extract_command, transcribe_voice

logger = logging.getLogger(__name__)

router = Router()


# ── Progress steps helper ──────────────────────────────

async def _edit_progress(msg: types.Message, step: str, total_steps: int,
                          current: int, detail: str = "") -> None:
    """Edit a message to show progress with step indicators."""
    bar = "▰" * current + "▱" * (total_steps - current)
    text = f"{step}\n\n<code>[{bar}]</code>"
    if detail:
        text += f"\n<i>{detail}</i>"
    await msg.edit_text(text, parse_mode="HTML")


# ── Gate ────────────────────────────────────────────────

def _is_admin(message: types.Message) -> bool:
    return message.from_user is not None and message.from_user.id == ADMIN_ID_INT


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
    logger.info("[voice] Admin %d sent voice message (msg_id=%d, file_id=%s)",
                admin_id, message.message_id, message.voice.file_id[:20])

    # Step 1: Downloading
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
    logger.info("Voice downloaded: %s (%d bytes)", tmp_path, voice.file_size or 0)

    # Step 2: Transcribing
    await _edit_progress(status_msg, "🔊 <b>Расшифровываю речь...</b>", total_steps, 2,
                          detail=f"Размер: {voice.file_size or '?'} байт")
    transcribed = await transcribe_voice(tmp_path)

    try:
        os.remove(tmp_path)
    except OSError:
        pass

    if not transcribed:
        await status_msg.edit_text(
            "❌ <b>Не удалось распознать голос.</b>\n\n"
            "Попробуйте ещё раз или напишите команду текстом.\n"
            "Пример: <i>Запиши Алину на 12:00 21 числа</i>",
            parse_mode="HTML",
        )
        return

    # Step 3: Analysing
    await _edit_progress(
        status_msg, "🔍 <b>Анализирую команду...</b>", total_steps, 3,
        detail=f"«{transcribed[:60]}{'...' if len(transcribed) > 60 else ''}»",
    )
    cmd = await extract_command(transcribed)

    # Step 4: Executing
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

    # Final: replace progress with result
    conf_emoji = {"high": "🎯", "medium": "👍", "low": "🤔"}.get(
        cmd.get("confidence", "medium"), "👍")
    await status_msg.edit_text(
        f"{result}\n\n"
        f"<i>🎤 «{transcribed}» {conf_emoji}</i>",
        parse_mode="HTML",
    )


# ── Text command handler ──────────────────────────────

@router.message(
    F.text,
    F.from_user.id == ADMIN_ID_INT,
    ~F.text.startswith("/"),
)
async def handle_admin_text_command(message: types.Message) -> None:
    """Admin text command → extract → execute → reply with progress."""
    text = message.text.strip()
    if not text:
        return

    cmd_indicators = [
        "запиш", "отмен", "удал", "покаж", "посмотр",
        "кто", "статус", "выходной", "открой", "закрой",
        "добавь слот", "добавь день",
    ]
    if not any(ind in text.lower() for ind in cmd_indicators):
        return

    admin_id = message.from_user.id
    logger.info("[voice:text] Admin %d text command: %s", admin_id, text[:100])

    # Progress message
    status_msg = await message.reply(
        f"💬 <b>Обрабатываю...</b>\n\n<code>[▰▰▱▱]</code>",
        parse_mode="HTML",
    )

    # Extract
    await _edit_progress(status_msg, "🔍 <b>Анализирую...</b>", 4, 3,
                          detail=f"«{text[:60]}{'...' if len(text) > 60 else ''}»")
    cmd = await extract_command(text)

    # Execute
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
