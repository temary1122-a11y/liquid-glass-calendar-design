"""
Bulk slot parser — pure regex, no API calls.

Formats supported:
  - "22.07 13:30; 14:00; 15:00"
  - "22.07 13:30, 14:00, 15:00"
  - "22.07\n13:30\n14:00\n15:00"
  - "31.0711:00" (glued: date + first time)
  - Mixed separators: "22.07 13:30; 14:00, 15:00; 23.07 10:00"

Returns: List[(date_str, time_str)] where date_str is "YYYY-MM-DD" and time_str is "HH:MM"
"""

import logging
import re
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r'^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$')

_RU_MONTH_RE = re.compile(
    r'^(\d{1,2})\s+(январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|'
    r'июн[ья]|июл[ья]|август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])$',
    re.IGNORECASE,
)

_TIME_RE = re.compile(r'^(\d{1,2})[:\.](\d{2})$')

_RU_MONTHS = {
    'января': 1, 'январь': 1, 'февраля': 2, 'февраль': 2,
    'марта': 3, 'март': 3, 'апреля': 4, 'апрель': 4,
    'мая': 5, 'май': 5, 'июня': 6, 'июнь': 6,
    'июля': 7, 'июль': 7, 'августа': 8, 'август': 8,
    'сентября': 9, 'сентябрь': 9, 'октября': 10, 'октябрь': 10,
    'ноября': 11, 'ноябрь': 11, 'декабря': 12, 'декабрь': 12,
}


def _parse_date(token: str) -> str:
    """Parse a date token into YYYY-MM-DD. Must be an exact date-only token."""
    today = datetime.now()
    default_year = today.year

    m = _DATE_RE.match(token)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else default_year
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-{day:02d}"

    m = _RU_MONTH_RE.match(token)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        month = _RU_MONTHS.get(month_name, 0)
        year = default_year
        if 1 <= day <= 31 and month:
            if month < today.month:
                year += 1
            return f"{year:04d}-{month:02d}-{day:02d}"

    return ""


def _parse_time(token: str) -> str:
    """Parse a time token like '13:30' or '13.30' into HH:MM."""
    m = _TIME_RE.match(token)
    if not m:
        return ""
    hour = int(m.group(1))
    minute = int(m.group(2))
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return ""


def parse_bulk(text: str) -> List[Tuple[str, str]]:
    """
    Parse bulk slot text into (YYYY-MM-DD, HH:MM) pairs.

    Algorithm (per line after splitting):
      For each line:
        - Unglue "DD.MMHH:MM" into "DD.MM HH:MM"
        - Try 1-token date, then 2-token Russian date
        - Remaining tokens are times
    """
    normalized = text.replace(',', '\n').replace(';', '\n')
    lines = [line.strip() for line in normalized.split('\n') if line.strip()]

    current_date = ""
    results: List[Tuple[str, str]] = []

    for line in lines:
        # Unglue: "31.0711:00" → "31.07 11:00"
        glued = re.match(r'^(\d{1,2}\.\d{1,2})(\d{1,2}[:\.]\d{2})(.*)$', line)
        if glued:
            line = f"{glued.group(1)} {glued.group(2)} {glued.group(3)}".strip()

        tokens = line.split()
        if not tokens:
            continue

        idx = 0
        found_date = ""

        d = _parse_date(tokens[idx])
        if d:
            found_date = d
            idx += 1
        elif len(tokens) >= 2:
            d = _parse_date(f"{tokens[0]} {tokens[1]}")
            if d:
                found_date = d
                idx += 2

        if found_date:
            current_date = found_date

        for tok in tokens[idx:]:
            t = _parse_time(tok)
            if t and current_date:
                results.append((current_date, t))

    seen = set()
    unique = []
    for pair in results:
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)

    logger.info("Bulk parse: %d lines → %d unique pairs", len(lines), len(unique))
    return unique
