"""
Client booking endpoints.

GET  /api/booking/available-dates  — public, returns available work days & slots
POST /api/booking/book             — public, creates a new booking
"""

import os
import httpx
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import Booking, TimeSlot, WorkDay, get_db
from api.websocket import manager as ws_manager

router = APIRouter(prefix="/api/booking", tags=["booking"])

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: str = os.getenv("ADMIN_ID", "")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def _send_telegram_message(chat_id: str | int, text: str) -> None:
    """Fire-and-forget: send a message via Telegram Bot API."""
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception as exc:
        print(f"[notify] Failed to send Telegram message: {exc}")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TimeSlotResponse(BaseModel):
    time: str
    available: bool


class WorkDayResponse(BaseModel):
    date: str
    slots: List[TimeSlotResponse]
    is_closed: bool


class BookingRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    date: str
    time: str
    service_id: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None


class BookingResponse(BaseModel):
    success: bool
    message: str
    booking_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/available-dates", response_model=List[WorkDayResponse])
async def get_available_dates(db: Session = Depends(get_db)):
    """
    Возвращает рабочие дни с доступными слотами.
    Прошедшие даты и закрытые дни исключаются.
    """
    today = datetime.now().date()

    work_days = (
        db.query(WorkDay)
        .filter(WorkDay.is_closed == False)  # noqa: E712
        .order_by(WorkDay.day_date)
        .all()
    )

    result: List[WorkDayResponse] = []

    for wd in work_days:
        try:
            wd_date = datetime.strptime(wd.day_date, "%Y-%m-%d").date()
        except ValueError:
            continue

        if wd_date < today:
            continue

        # Load slots manually (no relationship)
        slots = db.query(TimeSlot).filter(TimeSlot.day_date == wd.day_date).all()
        
        available_slots = [
            TimeSlotResponse(time=slot.slot_time, available=True)
            for slot in slots
            if slot.is_booked == 0
        ]

        # Include day even if all slots are booked (frontend decides what to show)
        all_slots = [
            TimeSlotResponse(time=slot.slot_time, available=slot.is_booked == 0)
            for slot in slots
        ]

        if all_slots:
            result.append(
                WorkDayResponse(
                    date=wd.day_date,
                    slots=all_slots,
                    is_closed=wd.is_closed,
                )
            )

    return result


@router.post("/book", response_model=BookingResponse)
async def create_booking(
    booking: BookingRequest,
    db: Session = Depends(get_db),
):
    """
    Создаёт новую запись.
    Проверяет что слот существует и не занят.
    """
    # Find work day
    work_day = db.query(WorkDay).filter(WorkDay.day_date == booking.date).first()
    if not work_day:
        return BookingResponse(success=False, message="Рабочий день не найден")

    if work_day.is_closed:
        return BookingResponse(success=False, message="Этот день закрыт")

    # Find free slot
    slot = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.day_date == booking.date,
            TimeSlot.slot_time == booking.time,
            TimeSlot.is_booked == 0,  # noqa: E712
        )
        .first()
    )

    if not slot:
        return BookingResponse(success=False, message="Слот не доступен или уже занят")

    new_booking = Booking(
        day_date=booking.date,
        slot_time=booking.time,
        user_id=booking.user_id,
        username=booking.username,
        client_name=booking.name,
        phone=booking.phone,
        status="pending",
        created_at=datetime.utcnow().isoformat(),  # ISO format string
    )

    try:
        db.add(new_booking)
        slot.is_booked = 1  # Integer instead of Boolean
        db.commit()
        db.refresh(new_booking)

        # Broadcast real-time update to all WebSocket clients
        await ws_manager.broadcast(
            {
                "type": "slot_booked",
                "data": {
                    "date": booking.date,
                    "time": booking.time,
                    "booking_id": new_booking.id,
                },
            }
        )

        # Notify admin about new booking
        phone_text = f"\n📞 Телефон: {booking.phone}" if booking.phone else ""
        username_text = f"\n👤 Telegram: @{booking.username}" if booking.username else ""
        admin_text = (
            f"🔔 <b>Новая запись</b>\n\n"
            f"👤 Имя: {booking.name}"
            f"{phone_text}"
            f"{username_text}"
            f"\n📅 Дата: {booking.date}"
            f"\n🕐 Время: {booking.time}"
            f"\n📝 Статус: Ожидает подтверждения"
        )
        await _send_telegram_message(ADMIN_ID, admin_text)

        return BookingResponse(
            success=True,
            message="Запись создана успешно",
            booking_id=new_booking.id,
        )
    except Exception as exc:
        db.rollback()
        return BookingResponse(success=False, message=f"Ошибка создания записи: {exc}")
