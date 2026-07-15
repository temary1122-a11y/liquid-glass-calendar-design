"""
Client booking endpoints.

GET  /api/booking/available-dates  — public, returns available work days & slots
POST /api/booking/book             — public, creates a new booking
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import ADMIN_ID
from database.db import Booking, TimeSlot, WorkDay, get_db
from api.websocket import manager as ws_manager
from utils.crypto import encrypt_phone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/booking", tags=["booking"])


# ---------------------------------------------------------------------------
# Pydantic schemas (with validation)
# ---------------------------------------------------------------------------


class TimeSlotResponse(BaseModel):
    time: str
    available: bool


class WorkDayResponse(BaseModel):
    date: str
    slots: List[TimeSlotResponse]
    is_closed: bool


class BookingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=5, max_length=5)
    service_id: Optional[str] = Field(default=None, max_length=50)
    user_id: Optional[int] = None
    username: Optional[str] = Field(default=None, max_length=255)


class BookingResponse(BaseModel):
    success: bool
    message: str
    booking_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _notify_admin_async(chat_id: str, text: str) -> None:
    """Send Telegram notification with error handling (fire-and-forget safe)."""
    try:
        from bot.bot import bot
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as exc:
        logger.warning("Failed to send admin notification: %s", exc)


def _create_notify_task(chat_id: str, text: str) -> None:
    """Spawn an asyncio task with proper error handling."""
    task = asyncio.create_task(_notify_admin_async(chat_id, text))
    task.add_done_callback(_handle_task_exception)


def _handle_task_exception(task: asyncio.Task) -> None:
    """Log any exception from a completed background task."""
    try:
        task.result()
    except Exception as exc:
        logger.warning("Background notification task failed: %s", exc)


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

        slots = db.query(TimeSlot).filter(TimeSlot.day_date == wd.day_date).all()

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

    # Check for existing booking on the SAME date only.
    # Clients can have multiple bookings on different dates,
    # but only one per date.
    if booking.user_id:
        existing_booking = (
            db.query(Booking)
            .filter(
                Booking.user_id == booking.user_id,
                Booking.status.notin_(["cancelled", "completed"]),
                Booking.day_date == booking.date,
            )
            .first()
        )
        if existing_booking:
            return BookingResponse(
                success=False,
                message=f"У вас уже есть запись на {booking.date}. Отмените её перед созданием новой."
            )

    new_booking = Booking(
        day_date=booking.date,
        slot_time=booking.time,
        user_id=booking.user_id,
        username=booking.username,
        client_name=booking.name,
        phone=encrypt_phone(booking.phone),
        status="pending",
        created_at=datetime.utcnow().isoformat(),
    )

    try:
        db.add(new_booking)
        slot.is_booked = 1
        db.commit()
        db.refresh(new_booking)

        # Отправка уведомления админу с error handling
        if ADMIN_ID:
            msg_text = (
                f"🔔 <b>Новая запись!</b>\n\n"
                f"👤 Имя: {booking.name}\n"
                f"📱 Телефон: {booking.phone or 'Не указан'}\n"
                f"📅 Дата: {booking.date}\n"
                f"⏰ Время: {booking.time}"
            )
            _create_notify_task(ADMIN_ID, msg_text)

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

        return BookingResponse(
            success=True,
            message="Запись создана успешно",
            booking_id=new_booking.id,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create booking: %s", exc)
        return BookingResponse(success=False, message=f"Ошибка создания записи: {exc}")
