"""
Admin command executor — processes parsed commands against the database.

All commands are admin-only. Each action validates slots/work_days
and returns a human-readable report for the admin.

Functions accept a SQLAlchemy Session so they can work with both
production (SessionLocal) and test (in-memory) databases.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database.db import Booking, TimeSlot, WorkDay
from utils.crypto import encrypt_phone

logger = logging.getLogger(__name__)


async def execute_command(cmd: dict, db: Session | None = None) -> str:
    """
    Execute a parsed admin command and return a report string.
    
    If db is None, creates a SessionLocal() (production mode).
    If db is provided, uses the given session (test mode).
    """
    action = cmd.get("action", "unknown")
    own_db = db is None

    if own_db:
        from database.db import SessionLocal
        db = SessionLocal()

    try:
        if action == "book":
            return _execute_book(db, cmd)
        elif action == "cancel":
            return _execute_cancel(db, cmd)
        elif action == "check":
            return _execute_check(db, cmd)
        elif action == "set_day_off":
            return _execute_set_day_status(db, cmd, closed=True)
        elif action == "set_day_on":
            return _execute_set_day_status(db, cmd, closed=False)
        else:
            return (
                "❓ Не удалось распознать команду.\n\n"
                "Попробуйте:\n"
                "• «Запиши Алину на 12:00 21 числа» — создать запись\n"
                "• «Отмени запись Алины» — отменить запись\n"
                "• «Кто записан 21 числа?» — посмотреть записи\n"
                "• «Выходной 21 числа» — закрыть день"
            )
    finally:
        if own_db and db:
            db.close()


# ---------------------------------------------------------------------------
# BOOK: create a booking
# ---------------------------------------------------------------------------


def _execute_book(db: Session, cmd: dict) -> str:
    name = cmd.get("client_name")
    date_str = cmd.get("date")
    time_str = cmd.get("time")

    if not name:
        return "❌ Не указано имя клиента. Например: «Запиши Алину на 12:00»"
    if not date_str:
        return "❌ Не указана дата. Например: «...на 21 числа» или «...на завтра»"
    if not time_str:
        return "❌ Не указано время. Например: «...на 12:00»"

    # Ensure work day exists
    work_day = db.query(WorkDay).filter(WorkDay.day_date == date_str).first()
    if not work_day:
        work_day = WorkDay(day_date=date_str, is_closed=0)
        db.add(work_day)
        db.flush()

    if work_day.is_closed:
        return f"❌ {date_str} — выходной день."

    # Check slot
    slot = db.query(TimeSlot).filter(
        TimeSlot.day_date == date_str, TimeSlot.slot_time == time_str,
    ).first()

    if slot and slot.is_booked:
        booking = db.query(Booking).filter(
            Booking.day_date == date_str,
            Booking.slot_time == time_str,
            Booking.status.notin_(["cancelled"]),
        ).first()
        occupied_by = booking.client_name if booking else "неизвестно"
        return f"❌ {time_str} {date_str} уже занято: {occupied_by}"

    if not slot:
        slot = TimeSlot(day_date=date_str, slot_time=time_str, is_booked=0)
        db.add(slot)
        db.flush()

    booking = Booking(
        day_date=date_str, slot_time=time_str,
        client_name=name, phone=encrypt_phone(None),
        status="confirmed", created_at=datetime.utcnow().isoformat(),
    )
    slot.is_booked = 1
    db.add(booking)
    db.commit()

    return (
        f"✅ <b>{name}</b> записан(а)!\n\n"
        f"📅 Дата: {_pretty_date(date_str)}\n"
        f"🕐 Время: {time_str}\n📌 Статус: подтверждена"
    )


# ---------------------------------------------------------------------------
# CANCEL
# ---------------------------------------------------------------------------


def _execute_cancel(db: Session, cmd: dict) -> str:
    name = cmd.get("client_name")
    date_str = cmd.get("date")
    time_str = cmd.get("time")
    reason = cmd.get("reason", "Отмена через команду")

    if not name and not date_str:
        return "❌ Укажите кого или с какого времени отменить."

    query = db.query(Booking).filter(Booking.status.notin_(["cancelled", "completed"]))
    if name:
        query = query.filter(Booking.client_name.ilike(f"%{name}%"))
    if date_str:
        query = query.filter(Booking.day_date == date_str)
    if time_str:
        query = query.filter(Booking.slot_time == time_str)

    bookings = query.all()

    if not bookings:
        return f"❌ Активная запись для «{name or 'указанных параметров'}» не найдена."

    if len(bookings) > 1:
        lines = ["⚠️ Найдено несколько записей:\n"]
        for b in bookings[:5]:
            lines.append(f"• {b.client_name} — {b.day_date} {b.slot_time}")
        return "\n".join(lines)

    b = bookings[0]
    slot = db.query(TimeSlot).filter(
        TimeSlot.day_date == b.day_date, TimeSlot.slot_time == b.slot_time,
    ).first()

    b.status = "cancelled"
    b.cancelled_at = datetime.utcnow().isoformat()
    b.cancel_reason = reason
    if slot:
        slot.is_booked = 0
    db.commit()

    return f"✅ Запись <b>{b.client_name}</b> отменена.\n📅 {b.day_date} {b.slot_time}\n📝 {reason}"


# ---------------------------------------------------------------------------
# CHECK
# ---------------------------------------------------------------------------


def _execute_check(db: Session, cmd: dict) -> str:
    date_str = cmd.get("date") or datetime.now().strftime("%Y-%m-%d")

    bookings = db.query(Booking).filter(
        Booking.day_date == date_str,
        Booking.status.notin_(["cancelled"]),
    ).order_by(Booking.slot_time).all()

    all_slots = db.query(TimeSlot).filter(
        TimeSlot.day_date == date_str,
    ).order_by(TimeSlot.slot_time).all()

    work_day = db.query(WorkDay).filter(WorkDay.day_date == date_str).first()

    if work_day and work_day.is_closed:
        return f"📴 {_pretty_date(date_str)} — выходной день"

    if not all_slots:
        return f"📅 {_pretty_date(date_str)} — нет слотов."

    lines = [f"📅 <b>{_pretty_date(date_str)}</b>\n"]
    by_time = {b.slot_time: b for b in bookings}
    for s in all_slots:
        booking = by_time.get(s.slot_time)
        if booking:
            icon = "✅" if booking.status == "confirmed" else "⏳"
            lines.append(f"{icon} {s.slot_time} — {booking.client_name}")
        else:
            lines.append(f"⬜ {s.slot_time} — свободно")
    lines.append(f"\nВсего записей: {len(bookings)}, свободно: {len(all_slots) - len(bookings)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SET_DAY_OFF / SET_DAY_ON
# ---------------------------------------------------------------------------


def _execute_set_day_status(db: Session, cmd: dict, closed: bool) -> str:
    date_str = cmd.get("date") or datetime.now().strftime("%Y-%m-%d")

    wd = db.query(WorkDay).filter(WorkDay.day_date == date_str).first()
    val = 1 if closed else 0
    if not wd:
        wd = WorkDay(day_date=date_str, is_closed=val)
        db.add(wd)
    else:
        wd.is_closed = val
    db.commit()

    if closed:
        # Cancel pending bookings
        pending = db.query(Booking).filter(
            Booking.day_date == date_str,
            Booking.status.in_(["pending", "confirmed"]),
        ).all()
        for b in pending:
            b.status = "cancelled"
            b.cancel_reason = f"День закрыт: {date_str}"
            b.cancelled_at = datetime.utcnow().isoformat()
        db.commit()
        if pending:
            return f"📴 {_pretty_date(date_str)} — выходной. Отменено: {len(pending)}"
        return f"📴 {_pretty_date(date_str)} — выходной"

    return f"📅 {_pretty_date(date_str)} — открыт"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
           "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def _pretty_date(date_str: str) -> str:
    try:
        y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
        target = datetime(y, m, d).date()
        today = datetime.now().date()
        if target == today:
            return f"Сегодня ({d} {_MONTHS[m]})"
        if target == today + timedelta(days=1):
            return f"Завтра ({d} {_MONTHS[m]})"
        if target == today + timedelta(days=2):
            return f"Послезавтра ({d} {_MONTHS[m]})"
        return f"{d} {_MONTHS[m]}"
    except Exception:
        return date_str
