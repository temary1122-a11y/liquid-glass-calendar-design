# ============================================================
# api/routes/booking.py — API endpoints для бронирования
# ============================================================

import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel
from api.websocket import manager

# Pydantic модель для отмены записи
class CancelBookingRequest(BaseModel):
    reason: str

from api.models import WorkDay, TimeSlot, BookingRequest, BookingResponse, MyBooking
from database.db import (
    get_available_work_days,
    get_free_slots,
    create_booking,
    get_user_booking,
    cancel_booking_by_id,
    get_booking_history,
    get_cancelled_bookings,
)

router = APIRouter(prefix="/api/booking", tags=["booking"])

# Rate limiter instance
def get_key_func(r=None):
    if r and r.client:
        return r.client.host
    elif r:
        return r.headers.get("x-forwarded-for", "")
    return "default"

limiter = Limiter(key_func=get_key_func)


@router.get("/available-dates", response_model=List[WorkDay])
@limiter.limit("60/minute")
async def get_available_dates(request: Request):
    """Получить доступные даты и слоты"""
    try:
        work_days = get_available_work_days()
        result = []

        for day in work_days:
            day_date = day["day_date"]
            slots = get_free_slots(day_date)
            time_slots = [
                TimeSlot(time=slot["slot_time"], available=True)
                for slot in slots
            ]
            result.append(
                WorkDay(
                    date=day_date,
                    slots=time_slots,
                    is_closed=bool(day["is_closed"])
                )
            )

        return result
    except Exception as e:
        logger.error(f"ERROR in available-dates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/book", response_model=BookingResponse)
@limiter.limit("5/hour")
async def create_booking_endpoint(request: Request, booking: BookingRequest):
    """Создать запись"""
    try:
        # Проверяем доступность слота
        available_slots = get_free_slots(booking.date)
        slot_times = [slot["slot_time"] for slot in available_slots]
        if booking.time not in slot_times:
            return BookingResponse(
                success=False,
                message="Этот слот недоступен"
            )

        # Создаём запись (user_id=0 для Mini App, username=None)
        booking_id = create_booking(
            user_id=0,
            username=None,
            client_name=booking.name,
            phone=booking.phone,
            day_date=booking.date,
            slot_time=booking.time,
            service_id=booking.service_id
        )

        if booking_id is None:
            return BookingResponse(
                success=False,
                message="Слот уже занят"
            )

        # Broadcast booking update to all connected clients
        await manager.send_booking_update(
            event_type="created",
            booking_data={
                "booking_id": booking_id,
                "date": booking.date,
                "time": booking.time,
                "name": booking.name,
                "phone": booking.phone,
                "service_id": booking.service_id
            }
        )

        return BookingResponse(
            success=True,
            message="Запись успешно создана",
            booking_id=booking_id
        )
    except ValueError:
        return BookingResponse(
            success=False,
            message="Неверный формат даты. Используйте ГГГГ-ММ-ДД"
        )
    except Exception as e:
        return BookingResponse(
            success=False,
            message=f"Ошибка: {str(e)}"
        )


@router.get("/my-bookings/{user_id}", response_model=List[MyBooking])
async def get_my_bookings(user_id: int):
    """Получить записи пользователя"""
    try:
        booking = get_user_booking(user_id)
        if not booking:
            return []

        return [
            MyBooking(
                id=booking["id"],
                date=booking["day_date"],
                time=booking["slot_time"],
                name=booking["client_name"],
                phone=booking["phone"]
            )
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cancel/{booking_id}")
@limiter.limit("10/hour")
async def cancel_booking_endpoint(request: Request, booking_id: int):
    """Отменить запись"""
    try:
        result = cancel_booking_by_id(booking_id)
        if result is None:
            return {"success": False, "message": "Запись не найдена"}

        # Broadcast booking update to all connected clients
        await manager.send_booking_update(
            event_type="cancelled",
            booking_data={"booking_id": booking_id}
        )

        return {"success": True, "message": "Запись отменена"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bookings/{booking_id}/cancel")
@limiter.limit("10/hour")
async def cancel_booking_with_reason(request: Request, booking_id: int, cancel_request: CancelBookingRequest):
    """Отменить запись с причиной"""
    try:
        result = cancel_booking_by_id(booking_id, cancel_request.reason)
        if result is None:
            return {"success": False, "message": "Запись не найдена"}
        return {"success": True, "message": "Запись отменена с причиной"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bookings/history")
@limiter.limit("30/minute")
async def get_booking_history_endpoint(request: Request):
    """Получить историю всех записей"""
    try:
        history = get_booking_history()
        return {"success": True, "bookings": [dict(row) for row in history]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bookings/cancelled")
@limiter.limit("30/minute")
async def get_cancelled_bookings_endpoint(request: Request):
    """Получить отмененные записи с причинами"""
    try:
        cancelled = get_cancelled_bookings()
        return {"success": True, "bookings": [dict(row) for row in cancelled]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
