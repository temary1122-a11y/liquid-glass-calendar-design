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
import re
from datetime import datetime, timedelta
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

# Russian month names for date parsing
_RU_MONTHS_MAP = {
    'января': 1, 'январь': 1, 'февраля': 2, 'февраль': 2,
    'марта': 3, 'март': 3, 'апреля': 4, 'апрель': 4,
    'мая': 5, 'май': 5, 'июня': 6, 'июнь': 6,
    'июля': 7, 'июль': 7, 'августа': 8, 'август': 8,
    'сентября': 9, 'сентябрь': 9, 'октября': 10, 'октябрь': 10,
    'ноября': 11, 'ноябрь': 11, 'декабря': 12, 'декабрь': 12,
}

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
# Command extraction (NLP) via Groq LLM
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """Ты — парсер голосовых команд администратора бьюти-салона.
Извлеки из текста команды структурированные данные. Отвечай ТОЛЬКО валидным JSON.

Реальные данные:
- Сегодня: {today}
- Завтра: {tomorrow}
- Послезавтра: {day_after_tomorrow}
- Текущий месяц: {current_month}

Команды и их значения (action):
- book — создать/добавить запись. Триггеры: "запиши", "забронируй", "поставь", "добавь",
  "добавь окно/окошко", "новое окно/окошко", "создай запись", "открой окно"
- cancel — отменить запись. Триггеры: "отмени", "удали", "сними", "убер"
- check — посмотреть записи. Триггеры: "покажи", "посмотри", "кто записан", "статус", "что там"
- set_day_off — закрыть день. Триггеры: "выходной", "закрой день", "нерабочий день"
- set_day_on — открыть день. Триггеры: "открой день", "рабочий день"
- unknown — непонятная команда

Даты (ВСЕГДА в YYYY-MM-DD):
- "сегодня" → {today}
- "завтра" → {tomorrow}
- "послезавтра" → {day_after_tomorrow}
- "15 числа" (без месяца) → 15-е число ТЕКУЩЕГО месяца ({current_month}-15)
- "15 июля" → 15 июля этого года
- "15.07" → 15 июля
- "21 числа следующего месяца" → {next_month}-21
- ЛЮБОЕ число без месяца = текущий месяц ({current_month})
- ЛЮБОЕ число с месяцем = указанный месяц этого года

Время (ВСЕГДА в HH:MM):
- "12:00", "12 часов", "в 12", "на 12", "к 12" → "12:00"
- "3 часа дня", "15 часов", "3 дня" → "15:00"
- "полдень" → "12:00", "полночь" → "00:00"
- "в 9 утра", "9 часов утра" → "09:00"
- "в 6 вечера", "6 часов вечера" → "18:00"
- Любое время с "дня/вечера/утра/ночи" — конвертируй в 24-часовой формат

Имя клиента (client_name):
- Извлекай имя из фраз: "запиши Алину", "Алина на 12", "добавь Диму", "Настю запиши"
- Игнорируй: "меня", "клиента", "человека" — это не имена
- Если нет имени — null
- Всегда с большой буквы

Примеры:

"запиши Алину на 12:00 21 числа" →
{{"action":"book","client_name":"Алина","date":"{current_month}-21","time":"12:00","confidence":"high"}}

"добавь окно завтра на 3 часа дня" →
{{"action":"book","client_name":null,"date":"{tomorrow}","time":"15:00","confidence":"high"}}

"новое окошко на 16:00 15 числа" →
{{"action":"book","client_name":null,"date":"{current_month}-15","time":"16:00","confidence":"high"}}

"запиши Диму 15 числа на 16 часов" →
{{"action":"book","client_name":"Дима","date":"{current_month}-15","time":"16:00","confidence":"high"}}

"запиши Настю на 3 часа дня" →
{{"action":"book","client_name":"Настя","date":null,"time":"15:00","confidence":"medium"}}

"кто записан 21 числа" →
{{"action":"check","client_name":null,"date":"{current_month}-21","time":null,"confidence":"high"}}

Верни ТОЛЬКО JSON, без markdown, без комментариев."""


async def extract_command(voice_text: str) -> dict:
    """
    Parse a natural-language admin command into structured data.
    Uses Llama 3.1 8B Instant (primary) with fallback to Llama 3.3 70B.
    Falls back to regex if both LLMs fail or Groq is unavailable.
    """
    if not GROQ_API_KEY:
        logger.info("GROQ_API_KEY not set — using regex fallback")
        return _regex_extraction(voice_text)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after_tomorrow = (now + timedelta(days=2)).strftime("%Y-%m-%d")
    current_month = now.strftime("%Y-%m")
    next_month = (now.replace(day=1) + timedelta(days=32)).strftime("%Y-%m")

    system_prompt = _EXTRACTION_SYSTEM_PROMPT.format(
        today=today,
        tomorrow=tomorrow,
        day_after_tomorrow=day_after_tomorrow,
        current_month=current_month,
        next_month=next_month,
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
        return _regex_extraction(voice_text)

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
# Regex-based extraction (fallback when Groq API is unavailable)
# ---------------------------------------------------------------------------

def _regex_extraction(text: str) -> dict:
    """
    Regex-based command extraction. Handles common patterns without API calls.
    Robust enough for realistic Russian voice commands.
    """
    text_lower = text.lower().strip()

    # ── Action detection ──
    if any(w in text_lower for w in ["запиш", "заброн", "постав", "добавь", "окно", "окошко", "создай запис", "открой окн"]):
        action = "book"
    elif any(w in text_lower for w in ["отмен", "удал", "сним", "убер"]):
        action = "cancel"
    elif any(w in text_lower for w in ["покаж", "посмотр", "кто", "статус", "записан", "что там"]):
        action = "check"
    elif any(w in text_lower for w in ["выходной", "закрой", "закрыт", "нерабоч"]):
        action = "set_day_off"
    elif any(w in text_lower for w in ["открой", "рабоч"]):
        action = "set_day_on"
    else:
        action = "unknown"

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    # ── Time extraction ──
    time_str = _extract_time(text_lower)

    # ── Date extraction ──
    date_str = None
    if any(w in text_lower for w in ["сегодня"]):
        date_str = today
    elif any(w in text_lower for w in ["завтра"]):
        date_str = tomorrow
    elif any(w in text_lower for w in ["послезавтра"]):
        date_str = day_after
    else:
        # "15 числа", "21 июля", "15.07"
        date_str = _extract_date(text_lower, now)

    # ── Name extraction ──
    name = _extract_name(text)

    return {
        "action": action,
        "client_name": name,
        "date": date_str,
        "time": time_str,
        "reason": None,
        "confidence": "low",
    }


def _extract_time(text: str) -> Optional[str]:
    """Extract time from Russian text. Returns HH:MM or None."""
    # "12:00", "12.00", "12-00"
    m = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # "3 часа дня", "в 3 дня", "15 часов"
    m = re.search(r'(?:в|на|к|)\s*(\d{1,2})\s*(?:часа?|часов|ч\b)\s*(дня|вечера|утра|ночи)?', text)
    if m:
        h = int(m.group(1))
        suffix = m.group(2)
        if suffix:
            if suffix == 'дня' and h <= 12:
                h += 12
            elif suffix == 'вечера':
                h += 12 if h < 12 else 0  # "6 вечера" = 18, "10 вечера" = 22
            elif suffix == 'ночи':
                h = h if h >= 12 else h  # "2 ночи" = 02, "12 ночи" = 00
                if h == 12:
                    h = 0
        else:
            # Just "15 часов" — could be 15:00, keep as-is if in 24h range
            if h > 12:
                pass  # already 24h
            else:
                # Ambiguous: "3 часа" without suffix — assume day (15:00)
                pass  # keep as literal
        if 0 <= h <= 23:
            return f"{h:02d}:00"

    # "полдень" / "полночь"
    if 'полдень' in text or 'полдня' in text:
        return "12:00"
    if 'полночь' in text or 'полночи' in text:
        return "00:00"

    # "в 12", "на 12", "к 12" (without hours/chasov)
    m = re.search(r'(?:в|на|к)\s+(\d{1,2})\b(?!\s*(?:час|ч\b|:\d))', text)
    if m:
        h = int(m.group(1))
        if 1 <= h <= 23:
            return f"{h:02d}:00"

    return None


def _extract_date(text: str, now: datetime) -> Optional[str]:
    """Extract date from text. Returns YYYY-MM-DD or None."""
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    # Relative
    if any(w in text for w in ["сегодня"]):
        return today
    if any(w in text for w in ["завтра"]):
        return tomorrow
    if any(w in text for w in ["послезавтра"]):
        return day_after

    # "15 числа" (current month)
    m = re.search(r'(\d{1,2})\s*числ[ао]', text)
    if m:
        day = int(m.group(1))
        if 1 <= day <= 31:
            return f"{now.year:04d}-{now.month:02d}-{day:02d}"

    # "22 июля", "15 августа"
    month_names = '|'.join(_RU_MONTHS_MAP.keys())
    m = re.search(rf'(\d{{1,2}})\s*({month_names})', text)
    if m:
        day = int(m.group(1))
        month = _RU_MONTHS_MAP.get(m.group(2).lower(), 0)
        if 1 <= day <= 31 and month:
            year = now.year
            if month < now.month:
                year += 1
            return f"{year:04d}-{month:02d}-{day:02d}"

    # "22.07", "22.7", "22/07"
    m = re.search(r'(\d{1,2})[\./](\d{1,2})', text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        if 1 <= day <= 31 and 1 <= month <= 12:
            year = now.year
            if month < now.month:
                year += 1
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None


def _extract_name(text: str) -> Optional[str]:
    """Extract a Russian client name from the command text.
    Normalizes accusative/accusative/dative cases to nominative."""
    # Words that look like names but aren't
    skip = {'меня', 'клиента', 'человека', 'окно', 'окошко', 'запись', 'слот',
            'новое', 'новый', 'новую', 'запиши', 'отмени', 'удали', 'покажи',
            'завтра', 'сегодня', 'записан', 'выходной', 'нерабочий'}

    # Normalize case ending to nominative
    def to_nom(name):
        n = name.capitalize()
        # Accusative -у/-ю: Алину→Алина, Настю→Настя, Свету→Света, Диму→Дима
        if n.endswith('у') and len(n) > 3:
            n = n[:-1] + 'а'
        elif n.endswith('ю') and len(n) > 3:
            n = n[:-1] + 'я'
        # Genitive -ы/-и: Алины→Алина, Насти→Настя
        elif n.endswith('ы') and len(n) > 3:
            n = n[:-1] + 'а'
        elif n.endswith('и') and len(n) > 3:
            n = n[:-1] + ('я' if n[-2] not in 'аоуыэяёюие' else 'а')
        return n

    # Pattern 1: "запиши Алину", "отмени запись Алины"
    m = re.search(
        r'(?:запиши|добавь|поставь|создай|отмени|удали|сними|убер[иь])\s+(?:запись\s+)?([А-ЯЁ][а-яё]+)',
        text, re.IGNORECASE,
    )
    if m:
        name = to_nom(m.group(1))
        if name.lower() not in skip:
            return name

    # Pattern 2: "Алина на 12", but not if preceded by non-name indicators
    m = re.search(
        r'(?<![а-яё])([А-ЯЁ][а-яё]+)\s+(?:на|в|к)\s+(?:\d|завтра)',
        text, re.IGNORECASE,
    )
    if m:
        name = to_nom(m.group(1))
        if name.lower() not in skip:
            return name

    # Pattern 3: trailing name "настю запиши", "диму добавь"
    m = re.search(
        r'([А-ЯЁ][а-яё]+[ую]?)\s+(?:запиши|добавь|отмени|удали|поставь)',
        text, re.IGNORECASE,
    )
    if m:
        name = to_nom(m.group(1).rstrip('ую'))
        if name.lower() not in skip:
            return name

    return None
