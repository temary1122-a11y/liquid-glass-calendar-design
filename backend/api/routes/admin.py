"""
Admin endpoints — all require admin initData verification.

Headers required:
  x-init-data: {Telegram WebApp initData}
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import verify_admin
from config import ADMIN_ID, BOT_TOKEN
from database.db import Booking, TimeSlot, WorkDay, get_db
from api.websocket import manager as ws_manager
from utils.crypto import decrypt_phone, encrypt_phone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
    data: Optional[Dict[str, Any]] = None


class AddSlotRequest(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=5, max_length=5)


class DeleteSlotRequest(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=5, max_length=5)


class CreateClientRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(default="", max_length=30)
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=5, max_length=5)
    username: Optional[str] = Field(default=None, max_length=255)
    user_id: Optional[int] = None
    note: Optional[str] = Field(default=None, max_length=1000)


class UpdateClientRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=5, max_length=5)
    username: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=20)


class DeleteClientRequest(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=5, max_length=5)


class NotifyCancellationRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=255)
    slot_time: str
    day_date: str
    reason: Optional[str] = Field(default=None, max_length=1000)


class AddWorkDayRequest(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    time_slots: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _send_telegram_message(chat_id: str | int, text: str) -> None:
    """Fire-and-forget: send a message via Telegram Bot API."""
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, skipping _send_telegram_message")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception as exc:
        logger.warning("Failed to send Telegram notification: %s", exc)


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
        slots = db.query(TimeSlot).filter(TimeSlot.day_date == wd.day_date).all()

        admin_slots: List[AdminSlot] = []
        for slot in slots:
            booking = db.query(Booking).filter(
                Booking.day_date == slot.day_date,
                Booking.slot_time == slot.slot_time
            ).first()

            booking_data: Optional[AdminBooking] = None
            if booking:
                booking_data = AdminBooking(
                    id=booking.id,
                    client_name=booking.client_name,
                    phone=decrypt_phone(booking.phone),
                    username=booking.username,
                    user_id=booking.user_id,
                    note=booking.note,
                    status=booking.status,
                )
            admin_slots.append(
                AdminSlot(time=slot.slot_time, is_booked=slot.is_booked == 1, booking=booking_data)
            )

        result[wd.day_date] = AdminWorkDay(
            day_date=wd.day_date,
            is_closed=wd.is_closed == 1,
            slots=admin_slots,
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
        new_wd = WorkDay(day_date=request.date, is_closed=0)
        db.add(new_wd)
        db.commit()

        if request.time_slots:
            for t in request.time_slots:
                db.add(TimeSlot(day_date=request.date, slot_time=t, is_booked=0))
            db.commit()

        await ws_manager.broadcast(
            {"type": "work_day_added", "data": {"date": request.date}}
        )

        return SuccessResponse(success=True, message="Рабочий день добавлен")
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to add work day: %s", exc)
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
        TimeSlot.day_date == request.date,
        TimeSlot.slot_time == request.time,
    ).first()
    if existing:
        return SuccessResponse(success=False, message="Слот уже существует")

    try:
        db.add(TimeSlot(day_date=request.date, slot_time=request.time, is_booked=0))
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
        logger.exception("Failed to add time slot: %s", exc)
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
        TimeSlot.day_date == request.date,
        TimeSlot.slot_time == request.time,
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
        logger.exception("Failed to delete time slot: %s", exc)
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
        TimeSlot.day_date == request.date,
        TimeSlot.slot_time == request.time,
        TimeSlot.is_booked == 0,
    ).first()

    if not slot:
        return SuccessResponse(success=False, message="Слот не доступен")

    try:
        booking = Booking(
            day_date=request.date,
            slot_time=request.time,
            user_id=request.user_id,
            username=request.username,
            client_name=request.name,
            phone=encrypt_phone(request.phone),
            note=request.note,
            status="confirmed",
            created_at=datetime.utcnow().isoformat(),
        )
        db.add(booking)
        slot.is_booked = 1
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
        logger.exception("Failed to create client: %s", exc)
        return SuccessResponse(success=False, message=f"Ошибка: {exc}")


@router.post("/update-client", response_model=SuccessResponse)
async def update_client(
    request: UpdateClientRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Обновить данные клиента по слоту (дата + время). Если booking не существует - создать новый."""
    work_day = db.query(WorkDay).filter(WorkDay.day_date == request.date).first()
    if not work_day:
        return SuccessResponse(success=False, message="Рабочий день не найден")

    slot = db.query(TimeSlot).filter(
        TimeSlot.day_date == request.date,
        TimeSlot.slot_time == request.time,
    ).first()

    if not slot:
        return SuccessResponse(success=False, message="Слот не найден")

    booking = db.query(Booking).filter(
        Booking.day_date == slot.day_date,
        Booking.slot_time == slot.slot_time
    ).first()

    try:
        old_status = None
        if not booking:
            booking = Booking(
                day_date=slot.day_date,
                slot_time=slot.slot_time,
                client_name=request.name,
                phone=encrypt_phone(request.phone),
                username=request.username,
                note=request.note,
                status=request.status or "pending",
                created_at=datetime.utcnow().isoformat(),
            )
            slot.is_booked = 1
            db.add(booking)
            logger.info("Admin created booking: username=%s status=%s", booking.username, booking.status)
        else:
            old_status = booking.status
            booking.client_name = request.name
            booking.phone = encrypt_phone(request.phone)
            if request.username is not None:
                booking.username = request.username
            booking.note = request.note
            if request.status:
                booking.status = request.status
            logger.info("Admin updated booking: username=%s old_status=%s new_status=%s",
                        booking.username, old_status, booking.status)

        db.commit()

        await ws_manager.broadcast(
            {
                "type": "booking_updated",
                "data": {"date": request.date, "time": request.time},
            }
        )

        logger.info("Chat opening check: old_status=%s request.status=%s username=%s user_id=%s",
                    old_status, request.status, booking.username, booking.user_id)

        # Determine what the frontend should do
        just_confirmed = old_status != "confirmed" and request.status == "confirmed"

        if just_confirmed:
            # Always send notification to client via bot (if user_id exists)
            if booking.user_id:
                try:
                    from bot.bot import bot
                    confirmation_text = (
                        f"✅ <b>Запись подтверждена!</b>\n\n"
                        f"📅 Дата: <b>{booking.day_date}</b>\n"
                        f"🕐 Время: <b>{booking.slot_time}</b>\n"
                        f"📍 Адрес: <b>Тихий переулок, 4</b>\n\n"
                        f"Ждём вас! 💕"
                    )
                    import asyncio
                    task = asyncio.create_task(
                        bot.send_message(chat_id=booking.user_id, text=confirmation_text)
                    )
                    task.add_done_callback(
                        lambda t: logger.warning("Failed to notify client: ***", t.exception())
                        if t.exception() else logger.info("Sent confirmation to client user_id=%s", booking.user_id)
                    )
                except Exception as notify_exc:
                    logger.warning("Failed to send client notification: ***", notify_exc)

            # If client has a username, tell frontend to open chat with pre-filled message
            if booking.username:
                logger.info("Opening admin chat: username=%s old_status=%s", booking.username, old_status)
                return SuccessResponse(
                    success=True,
                    message="Запись подтверждена",
                    data={
                        "type": "open_chat",
                        "username": booking.username,
                        "text": (
                            f"✅ Записала\n\n"
                            f"📅 Дата: {booking.day_date}\n"
                            f"🕐 Время: {booking.slot_time}\n"
                            f"📍 Адрес: Тихий переулок, 4\n\n"
                            f"📹 Видео: https://t.me/lashessoto4ka/8"
                        ),
                    },
                )
            else:
                logger.info("Client confirmed but no username — notification sent via bot")
                return SuccessResponse(
                    success=True,
                    message="Запись подтверждена. Клиент уведомлен через бота.",
                )
        else:
            logger.info("Not a confirmation: old_status=%s request.status=%s", old_status, request.status)
            return SuccessResponse(success=True, message="Запись обновлена")
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update client: %s", exc)
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
        TimeSlot.day_date == request.date,
        TimeSlot.slot_time == request.time,
    ).first()

    if not slot:
        return SuccessResponse(success=False, message="Слот не найден")

    booking = db.query(Booking).filter(
        Booking.day_date == slot.day_date,
        Booking.slot_time == slot.slot_time
    ).first()

    try:
        if booking:
            db.delete(booking)
        slot.is_booked = 0
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
        logger.exception("Failed to delete client: %s", exc)
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
    await _send_telegram_message(ADMIN_ID, text)
    return {"ok": True}


@router.get("/archive")
async def get_archive(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """
    Получить архивированные записи (completed, cancelled).
    Сортировка по дате создания (сначала самые новые).
    """
    archive_bookings = db.query(Booking).filter(
        Booking.status.in_(["completed", "cancelled"])
    ).order_by(Booking.created_at.desc()).all()

    return [
        {
            "id": b.id,
            "client_name": b.client_name,
            "phone": decrypt_phone(b.phone),
            "day_date": b.day_date,
            "slot_time": b.slot_time,
            "status": b.status,
            "cancelled_at": b.cancelled_at,
            "cancel_reason": b.cancel_reason,
            "created_at": b.created_at,
        }
        for b in archive_bookings
    ]
