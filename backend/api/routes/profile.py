"""
Client profile endpoints.

GET  /api/profile/bookings?user_id={id}  — requires x-init-data header
POST /api/profile/cancel                 — requires x-init-data header
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user_id
from database.db import Booking, get_db
from api.websocket import manager as ws_manager

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class UserBookingResponse(BaseModel):
    id: int
    client_name: str
    phone: Optional[str] = None
    day_date: str
    slot_time: str
    status: str
    is_cancelled: bool
    cancel_reason: Optional[str] = None
    created_at: str
    cancelled_at: Optional[str] = None


class CancelRequest(BaseModel):
    booking_id: int
    reason: str
    user_id: int


class CancelResponse(BaseModel):
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/bookings", response_model=List[UserBookingResponse])
async def get_user_bookings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Возвращает все записи пользователя.
    user_id в query должен совпадать с user_id из initData.
    """
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    result: List[UserBookingResponse] = []
    for b in bookings:
        # Direct fields from Booking (no relationships)
        result.append(
            UserBookingResponse(
                id=b.id,
                client_name=b.client_name,
                phone=b.phone,
                day_date=b.day_date,  # Direct field
                slot_time=b.slot_time,  # Direct field
                status=b.status,
                is_cancelled=b.is_cancelled == 1,  # Integer to Boolean
                cancel_reason=b.cancel_reason,  # Renamed field
                created_at=b.created_at,  # Already ISO string
                cancelled_at=b.cancelled_at,  # Already ISO string
            )
        )

    return result


@router.post("/cancel", response_model=CancelResponse)
async def cancel_booking(
    request: CancelRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Отменяет запись пользователя.
    Проверяет что booking принадлежит текущему пользователю.
    """
    if request.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == request.booking_id,
            Booking.user_id == request.user_id,
        )
        .first()
    )

    if not booking:
        return CancelResponse(success=False, message="Запись не найдена")

    if booking.status == "cancelled":
        return CancelResponse(success=False, message="Запись уже отменена")

    try:
        booking.status = "cancelled"
        booking.is_cancelled = 1  # Integer
        booking.cancelled_at = datetime.utcnow().isoformat()  # ISO string
        booking.cancel_reason = request.reason

        # Find and update slot manually (no relationship)
        slot = db.query(TimeSlot).filter(
            TimeSlot.day_date == booking.day_date,
            TimeSlot.slot_time == booking.slot_time
        ).first()
        if slot:
            slot.is_booked = 0  # Integer
            work_day = db.query(WorkDay).filter(WorkDay.day_date == booking.day_date).first()

        db.commit()

        # Broadcast real-time update
        await ws_manager.broadcast(
            {
                "type": "booking_cancelled",
                "data": {
                    "booking_id": booking.id,
                    "date": work_day.day_date if work_day else None,
                    "time": slot.time if slot else None,
                    "reason": request.reason,
                },
            }
        )

        return CancelResponse(success=True, message="Запись успешно отменена")
    except Exception as exc:
        db.rollback()
        return CancelResponse(success=False, message=f"Ошибка отмены: {exc}")
