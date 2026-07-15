"""
Bulk slot parser — parses admin messages with date+time blocks.

Format examples:
  22.07 13:30;
  24.07 13:30;
  28.07 13:30; 16:00
  29.07 11:00; 13:30; 16:00
  31.0711:00; 13:30; 16:00   ← glued date+time (no space)

Handles:
  - Multiple dates, each with multiple time slots
  - Glued date+time (no space between date and first slot)
  - Extra whitespace, empty lines
  - Various separators: ; or , or newline between slots
  - Continuation lines (times on next line for current date)
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

_DATE_RE = re.compile(r"(\d{1,2})\s*[\.\s]\s*(\d{1,2})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def parse_bulk_slots(text: str, year: int | None = None) -> Dict[str, List[str]]:
    """Parse bulk slot text → {"2026-07-22": ["13:30", "16:00"], ...}"""
    if year is None:
        year = datetime.now().year

    result: Dict[str, List[str]] = defaultdict(list)

    # Normalize separators
    text = text.replace(";", "\n").replace(",", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return {}

    current_date: str | None = None

    for line in lines:
        date_match = _DATE_RE.match(line)

        if date_match:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                current_date = f"{year}-{month:02d}-{day:02d}"
                remainder = line[date_match.end():].strip()
                for t in _extract_times(remainder):
                    result[current_date].append(t)

        elif current_date:
            # Continuation: times on their own line after a date line
            for t in _extract_times(line):
                result[current_date].append(t)

    # Deduplicate and sort
    for dk in list(result.keys()):
        unique = sorted(set(result[dk]))
        if unique:
            result[dk] = unique
        else:
            del result[dk]

    return dict(sorted(result.items()))


def _extract_times(text: str) -> List[str]:
    times = []
    for m in _TIME_RE.finditer(text):
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            times.append(f"{h:02d}:{mn:02d}")
    return times


def parse_bulk_slots_and_execute(text: str, db_session) -> str:
    """Parse and create slots in DB. Returns summary message."""
    from database.db import WorkDay, TimeSlot

    slots = parse_bulk_slots(text)
    if not slots:
        return (
            "❌ Не удалось распознать даты и время.\n\n"
            "<i>Пример:\n22.07 13:30;\n24.07 13:30;\n28.07 13:30; 16:00</i>"
        )

    created_dates = 0
    created_slots = 0
    skipped = 0
    lines: List[str] = []

    for date_str, times in slots.items():
        wd = db_session.query(WorkDay).filter(WorkDay.day_date == date_str).first()
        if not wd:
            wd = WorkDay(day_date=date_str, is_closed=False)
            db_session.add(wd)
            db_session.flush()
            created_dates += 1

        for t in times:
            ex = db_session.query(TimeSlot).filter(
                TimeSlot.day_date == date_str, TimeSlot.slot_time == t
            ).first()
            if ex:
                skipped += 1
                continue
            db_session.add(TimeSlot(day_date=date_str, slot_time=t, is_booked=0))
            created_slots += 1

        lines.append(f"📅 {date_str}: {', '.join(times)}")

    db_session.commit()

    s = f"✅ <b>Массовое добавление</b>\n\n📅 Дней: <b>{created_dates}</b>\n🕐 Слотов: <b>{created_slots}</b>\n"
    if skipped:
        s += f"⏭️ Уже есть: <b>{skipped}</b>\n"
    return s + "\n" + "\n".join(lines)
