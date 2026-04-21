"""
Admin endpoints — all require HMAC admin signature.

Headers required:
  x-admin-id: {ADMIN_ID}
  x-admin-signature: {signature}
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import verify_admin
from database.db import Booking, TimeSlot, WorkDay, get_db
from api.websocket import manager as ws_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: str = os.getenv("ADMIN_ID", "")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AdminBooking(BaseModel):
    id: int
    client_name: str
    phone: Optional[str] = None
    username: Optional[str] = None
    user_id: Optional[int] = None
    note: Optional[str] = None
    status: str


class AdminSlot(BaseModel):
    time: str
    is_booked: bool
    booking: Optional[AdminBooking] = None


class AdminWorkDay(BaseModel):
    day_date: str
    is_closed: bool
    slots: List[AdminSlot]


class SuccessResponse(BaseModel):
    success: bool
    message: str
    booking_id: Optional[int] = None


class AddSlotRequest(BaseModel):
    date: str
    time: str


class DeleteSlotRequest(BaseModel):
    date: str
    time: str


class CreateClientRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    username: Optional[str] = None
    user_id: Optional[int] = None
    note: Optional[str] = None


class UpdateClientRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    username: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None


class DeleteClientRequest(BaseModel):
    date: str
    time: str


class NotifyCancellationRequest(BaseModel):
    client_name: str
    slot_time: str
    day_date: str
    reason: Optional[str] = None


class AddWorkDayRequest(BaseModel):
    date: str
    time_slots: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Helper
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
# Routes
# ---------------------------------------------------------------------------


@router.get("/work-days-with-bookings", response_model=Dict[str, AdminWorkDay])
async def get_work_days_with_bookings(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Все рабочие дни с информацией о слотах и записях."""
    work_days = db.query(WorkDay).order_by(WorkDay.day_date).all()

    result: Dict[str, AdminWorkDay] = {}
    for wd in work_days:
        slots: List[AdminSlot] = []
        for slot in wd.slots:
            booking_data: Optional[AdminBooking] = None
            if slot.booking:
                b = slot.booking
                booking_data = AdminBooking(
                    id=b.id,
                    client_name=b.client_name,
                    phone=b.phone,
                    username=b.username,
                    user_id=b.user_id,
                    note=b.note,
                    status=b.status,
                )
            slots.append(
                AdminSlot(time=slot.time, is_booked=slot.is_booked, booking=booking_data)
            )

        result[wd.day_date] = AdminWorkDay(
            day_date=wd.day_date,
            is_closed=wd.is_closed,
            slots=slots,
        )

    return result


@router.post("/add-work-day", response_model=SuccessResponse)
async def add_work_day(
    request: AddWorkDayRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Добавить рабочий день (опционально со слотами)."""
    existing = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if existing:
        return SuccessResponse(success=False, message="Рабочий день уже существует")

    try:
        new_wd = WorkDay(day_date=request.date, is_closed=False)
        db.add(new_wd)
        db.flush()  # get new_wd.id without committing

        if request.time_slots:
            for t in request.time_slots:
                db.add(TimeSlot(day_id=new_wd.id, time=t))

        db.commit()

        await ws_manager.broadcast(
            {"type": "work_day_added", "data": {"date": request.date}}
        )

        return SuccessResponse(success=True, message="Рабочий день добавлен")
    except Exception as exc:
        db.rollback()
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/add-time-slot", response_model=SuccessResponse)
async def add_time_slot(
    request: AddSlotRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Добавить временной слот в рабочий день."""
    work_day = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if not work_day:
        return SuccessResponse(success=False, message="Рабочий день не найден")

    existing = db.query(TimeSlot).filter(
        TimeSlot.day_id == work_day.id,
        TimeSlot.time == request.time,
    ).first()
    if existing:
        return SuccessResponse(success=False, message="Слот уже существует")

    try:
        db.add(TimeSlot(day_id=work_day.id, time=request.time))
        db.commit()

        await ws_manager.broadcast(
            {
                "type": "slot_added",
                "data": {"date": request.date, "time": request.time},
            }
        )

        return SuccessResponse(success=True, message="Слот добавлен")
    except Exception as exc:
        db.rollback()
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/delete-time-slot", response_model=SuccessResponse)
async def delete_time_slot(
    request: DeleteSlotRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Удалить временной слот."""
    work_day = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if not work_day:
        return SuccessResponse(success=False, message="Рабочий день не найден")

    slot = db.query(TimeSlot).filter(
        TimeSlot.day_id == work_day.id,
        TimeSlot.time == request.time,
    ).first()

    if not slot:
        return SuccessResponse(success=False, message="Слот не найден")

    try:
        db.delete(slot)
        db.commit()

        await ws_manager.broadcast(
            {
                "type": "slot_deleted",
                "data": {"date": request.date, "time": request.time},
            }
        )

        return SuccessResponse(success=True, message="Слот удалён")
    except Exception as exc:
        db.rollback()
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/create-client", response_model=SuccessResponse)
async def create_client(
    request: CreateClientRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Создать запись клиента вручную (от имени админа)."""
    work_day = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if not work_day:
        return SuccessResponse(success=False, message="Рабочий день не найден")

    slot = db.query(TimeSlot).filter(
        TimeSlot.day_id == work_day.id,
        TimeSlot.time == request.time,
        TimeSlot.is_booked == False,  # noqa: E712
    ).first()

    if not slot:
        return SuccessResponse(success=False, message="Слот не доступен")

    try:
        booking = Booking(
            slot_id=slot.id,
            user_id=request.user_id,
            username=request.username,
            client_name=request.name,
            phone=request.phone,
            note=request.note,
            status="confirmed",  # admin-created bookings are confirmed immediately
        )
        db.add(booking)
        slot.is_booked = True
        db.commit()
        db.refresh(booking)

        await ws_manager.broadcast(
            {
                "type": "slot_booked",
                "data": {
                    "date": request.date,
                    "time": request.time,
                    "booking_id": booking.id,
                },
            }
        )

        return SuccessResponse(
            success=True, message="Запись создана", booking_id=booking.id
        )
    except Exception as exc:
        db.rollback()
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/update-client", response_model=SuccessResponse)
async def update_client(
    request: UpdateClientRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Обновить данные клиента по слоту (дата + время)."""
    work_day = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if not work_day:
        return SuccessResponse(success=False, message="Рабочий день не найден")

    slot = db.query(TimeSlot).filter(
        TimeSlot.day_id == work_day.id,
        TimeSlot.time == request.time,
    ).first()

    if not slot or not slot.booking:
        return SuccessResponse(success=False, message="Запись не найдена")

    try:
        slot.booking.client_name = request.name
        slot.booking.phone = request.phone
        slot.booking.username = request.username
        slot.booking.note = request.note
        if request.status:
            slot.booking.status = request.status
        db.commit()

        await ws_manager.broadcast(
            {
                "type": "booking_updated",
                "data": {"date": request.date, "time": request.time},
            }
        )

        return SuccessResponse(success=True, message="Запись обновлена")
    except Exception as exc:
        db.rollback()
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/delete-client", response_model=SuccessResponse)
async def delete_client(
    request: DeleteClientRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Удалить запись клиента из слота."""
    work_day = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if not work_day:
        return SuccessResponse(success=False, message="Рабочий день не найден")

    slot = db.query(TimeSlot).filter(
        TimeSlot.day_id == work_day.id,
        TimeSlot.time == request.time,
    ).first()

    if not slot:
        return SuccessResponse(success=False, message="Слот не найден")

    try:
        if slot.booking:
            db.delete(slot.booking)
        slot.is_booked = False
        db.commit()

        await ws_manager.broadcast(
            {
                "type": "slot_freed",
                "data": {"date": request.date, "time": request.time},
            }
        )

        return SuccessResponse(success=True, message="Запись удалена")
    except Exception as exc:
        db.rollback()
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/notify-cancellation")
async def notify_cancellation(
    request: NotifyCancellationRequest,
    _: bool = Depends(verify_admin),
):
    """
    Отправить уведомление админу об отмене записи (fire-and-forget).
    Frontend вызывает этот endpoint после отмены.
    """
    reason_text = request.reason or "Причина не указана"
    text = (
        f"🔔 <b>Запись отменена</b>\n\n"
        f"👤 Имя: {request.client_name}\n"
        f"📅 Дата: {request.day_date}\n"
        f"🕐 Время: {request.slot_time}\n"
        f"❌ Причина: {reason_text}"
    )
    # fire-and-forget — не ждём результата
    await _send_telegram_message(ADMIN_ID, text)
    return {"ok": True}
