# ============================================================
# api/routes/booking.py — Routes для записи
# ============================================================

from fastapi import APIRouter, HTTPException, Request
from typing import List
from datetime import datetime, timedelta
from dataclasses import dataclass
from slowapi import Limiter

# Dataclass для отмены записи
@dataclass
class CancelBookingRequest:
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
limiter = Limiter(key_func=lambda r: r.client.host if r.client else r.headers.get("x-forwarded-for", ""))


@router.get("/available-dates")
@limiter.limit("60/minute")
async def get_available_dates(request: Request):
    """Получить доступные даты и слоты"""
    try:
        work_days = get_available_work_days()
        result = []

        for day in work_days:
            slots = get_free_slots(day[1])  # day[1] = day_date
            time_slots = [
                TimeSlot(time=slot[2], available=True)  # slot[2] = slot_time (исправлено)
                for slot in slots
            ]
            result.append(
                WorkDay(
                    date=day[1],  # day_date
                    slots=time_slots,
                    is_closed=bool(day[2])  # is_closed
                )
            )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/book")
@limiter.limit("5/hour")
async def create_booking_endpoint(request: Request, booking: BookingRequest):
    """Создать запись"""
    try:
        # Проверяем доступность слота
        available_slots = get_free_slots(booking.date)
        slot_times = [slot[1] for slot in available_slots]  # slot[1] = slot_time
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


@router.get("/my-bookings/{user_id}")
async def get_my_bookings(user_id: int):
    """Получить записи пользователя"""
    try:
        booking = get_user_booking(user_id)
        if not booking:
            return []

        return [
            MyBooking(
                id=booking[0],  # id
                date=booking[5],  # day_date
                time=booking[6],  # slot_time
                name=booking[3],  # client_name
                phone=booking[4]  # phone
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
