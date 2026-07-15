"""
Groq API client — voice transcription + structured command extraction.

Free tier details (as documented by Groq at console.groq.com):
  - Whisper transcription: whisper-large-v3-turbo (fast, multilingual incl. Russian)
  - LLM: llama-3.1-8b-instant (fastest free model, supports JSON mode)
  - Fallback LLM: llama-3.3-70b-versatile (more powerful for complex commands)
  - Rate limits: ~30 req/min text, ~14K RPM tokens for instant models
  - Free tier: ✅ confirmed — no credit card needed for initial usage

Uses GROQ_API_KEY from config. If not set, voice transcription is skipped
and only text commands work.
"""

import json
import logging
import os
from typing import Optional

import httpx

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROQ_BASE = "https://api.groq.com/openai/v1"

# Primary models (fast + free)
TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
EXTRACTION_MODEL = "llama-3.1-8b-instant"

# Fallback model (more powerful, still free)
FALLBACK_EXTRACTION_MODEL = "llama-3.3-70b-versatile"

# Timeouts
TRANSCRIPTION_TIMEOUT = 60.0  # voice takes longer
EXTRACTION_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Voice transcription
# ---------------------------------------------------------------------------


def _fix_ext(name: str) -> str:
    """Telegram sends .oga — Groq expects .ogg."""
    if name.endswith('.oga'):
        return name[:-4] + '.ogg'
    return name


async def transcribe_voice(audio_path: str) -> Optional[str]:
    """
    Transcribe an audio file using Groq Whisper API.
    Args:
        audio_path: Path to .ogg/.mp3 audio file
    Returns:
        Transcribed text, or None on failure
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — skipping voice transcription")
        return None

    url = f"{GROQ_BASE}/audio/transcriptions"

    try:
        async with httpx.AsyncClient(timeout=TRANSCRIPTION_TIMEOUT) as client:
            with open(audio_path, "rb") as f:
                filename = _fix_ext(os.path.basename(audio_path))
                files = {
                    "file": (filename, f, "audio/ogg"),
                }
                data = {
                    "model": TRANSCRIPTION_MODEL,
                    "language": "ru",  # hint for better Russian recognition
                    "response_format": "text",
                }
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                }

                resp = await client.post(url, files=files, data=data, headers=headers)

            if resp.status_code == 200:
                text = resp.text.strip()
                logger.info("Transcription success: %s", text[:100])
                return text
            else:
                logger.error(
                    "Transcription failed: HTTP %d — %s",
                    resp.status_code, resp.text[:300],
                )
                return None

    except Exception as exc:
        logger.error("Transcription exception: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Command extraction (NLP)
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """Ты — парсер голосовых команд администратора бьюти-салона.
Извлеки из текста команды структурированные данные.

Текущая дата: {today}

Правила:
- Если клиент говорит "запиши/забронируй/поставь ИМЯ на ВРЕМЯ ЧИСЛА" → action="book"
- Если "отмени/удали/сними запись ИМЯ" → action="cancel"
- Если "покажи/посмотри/кто записан/статус на ДАТУ" → action="check"
- Если "открой/закрой/выходной ДАТУ" → action="set_day_off" или "set_day_on"
- Непонятная команда → action="unknown"

Даты:
- "сегодня" → {today}
- "завтра" → {tomorrow}
- "послезавтра" → {day_after_tomorrow}
- "21 числа"/"21 июля"/"21.07" → YYYY-MM-DD
- Если месяц не указан — используй текущий месяц ({current_month})
- Если число не число месяца — игнорируй (action="unknown")

Время:
- "12:00"/"в 12"/"на 12"/"12 часов" → "HH:MM"
- Всегда в формате HH:MM (с ведущим нулём)

Верни ТОЛЬКО валидный JSON, без markdown, без комментариев:
{{
  "action": "book" | "cancel" | "check" | "set_day_off" | "set_day_on" | "unknown",
  "client_name": "имя клиента или null",
  "date": "YYYY-MM-DD или null",
  "time": "HH:MM или null",
  "reason": "причина или null",
  "confidence": "high" | "medium" | "low"
}}"""


async def extract_command(voice_text: str) -> dict:
    """
    Parse a natural-language admin command into structured data.
    Uses Llama 3.1 8B Instant (primary) with fallback to Llama 3.3 70B.

    Args:
        voice_text: Raw transcribed text from voice or typed command

    Returns:
        Parsed command dict with action/client_name/date/time
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — cannot extract command")
        return _fallback_regex_extraction(voice_text)

    from datetime import datetime, timedelta

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after_tomorrow = (now + timedelta(days=2)).strftime("%Y-%m-%d")
    current_month = now.strftime("%Y-%m")

    system_prompt = _EXTRACTION_SYSTEM_PROMPT.format(
        today=today,
        tomorrow=tomorrow,
        day_after_tomorrow=day_after_tomorrow,
        current_month=current_month,
    )

    # Try primary model first
    result = await _call_llm(
        model=EXTRACTION_MODEL,
        system_prompt=system_prompt,
        user_message=voice_text,
        timeout=EXTRACTION_TIMEOUT,
    )

    if result is None:
        logger.warning("Primary model failed, trying fallback...")
        result = await _call_llm(
            model=FALLBACK_EXTRACTION_MODEL,
            system_prompt=system_prompt,
            user_message=voice_text,
            timeout=EXTRACTION_TIMEOUT * 2,
        )

    if result is None:
        return _fallback_regex_extraction(voice_text)

    return result


async def _call_llm(
    model: str,
    system_prompt: str,
    user_message: str,
    timeout: float = 15.0,
) -> Optional[dict]:
    """Call Groq chat completions and parse JSON response."""
    url = f"{GROQ_BASE}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
            )

        if resp.status_code == 200:
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            try:
                result = json.loads(content)
                logger.info("LLM extraction: %s → %s", user_message[:80], result)
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON: %s", content[:200])
                return None
        else:
            logger.error(
                "LLM call failed: HTTP %d — %s",
                resp.status_code, resp.text[:300],
            )
            return None

    except Exception as exc:
        logger.error("LLM call exception: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Fallback: regex-based extraction (when Groq API is unavailable)
# ---------------------------------------------------------------------------


def _fallback_regex_extraction(text: str) -> dict:
    """
    Simple regex-based command extraction as fallback.
    Handles the most common patterns without any API calls.
    """
    import re
    from datetime import datetime, timedelta

    text_lower = text.lower().strip()

    # Detect action
    if any(w in text_lower for w in ["запиш", "заброн", "постав", "добав", "созда"]):
        action = "book"
    elif any(w in text_lower for w in ["отмен", "удал", "сним", "убер"]):
        action = "cancel"
    elif any(w in text_lower for w in ["покаж", "посмотр", "кто", "статус", "записан"]):
        action = "check"
    elif any(w in text_lower for w in ["выходной", "закрыт", "нерабоч"]):
        action = "set_day_off"
    elif any(w in text_lower for w in ["открыт", "рабоч"]):
        action = "set_day_on"
    else:
        action = "unknown"

    # Extract time
    time_match = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if not time_match:
        time_match = re.search(r'(?:в|на|к)\s*(\d{1,2})\b(?!\d|\.\d)', text)
    time_str = None
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.lastindex and time_match.lastindex >= 2 else 0
        time_str = f"{hour:02d}:{minute:02d}"

    # Extract date
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after_tomorrow_str = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    date_str = None
    if any(w in text_lower for w in ["сегодня"]):
        date_str = today_str
    elif any(w in text_lower for w in ["завтра"]):
        date_str = tomorrow_str
    elif any(w in text_lower for w in ["послезавтра"]):
        date_str = day_after_tomorrow_str
    else:
        # Match "21 числа", "21 июля", "21.07", "21/07"
        date_match = re.search(r'(\d{1,2})\s*(?:числа|\.(\d{1,2})|/(\d{1,2}))', text)
        if date_match:
            day = int(date_match.group(1))
            month = date_match.group(2) or date_match.group(3)
            if month:
                month = int(month)
            else:
                month = now.month
            year = now.year
            # If month < current month, assume next year
            if month < now.month:
                year += 1
            date_str = f"{year}-{month:02d}-{day:02d}"

    # Extract client name
    name = None
    # Pattern: "запиши Алину", "Алина на 12"
    name_match = re.search(
        r'(?:запиш[иь]|добав[ь]|постав[ь]|отмен[иь]|убер[иь])\s+([А-ЯЁ][а-яё]+)',
        text, re.IGNORECASE,
    )
    if name_match:
        name = name_match.group(1).capitalize()
    else:
        # Pattern: "Алину на 12:00", "Свету удали"
        name_match = re.search(
            r'([А-ЯЁ][а-яё]+)(?:у|а|е|ю)?\s+(?:на|в|запиш|отмен|удал)',
            text, re.IGNORECASE,
        )
        if name_match:
            name = name_match.group(1).capitalize()

    logger.info("Regex fallback: %s → action=%s name=%s date=%s time=%s",
                text[:100], action, name, date_str, time_str)

    return {
        "action": action,
        "client_name": name,
        "date": date_str,
        "time": time_str,
        "reason": None,
        "confidence": "low",
    }
