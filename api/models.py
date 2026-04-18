# ============================================================
# api/models.py — Pydantic модели для API (Pydantic 1.x)
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List


class TimeSlot(BaseModel):
    """Временной слот"""
    time: str
    available: bool


class WorkDay(BaseModel):
    """Рабочий день"""
    date: str
    slots: List[TimeSlot]
    is_closed: bool = False


class Service(BaseModel):
    """Услуга"""
    id: str
    name: str
    price: int


class BookingRequest(BaseModel):
    """Запрос на запись"""
    date: str
    time: str
    name: str
    phone: str
    service_id: str  # ID услуги


class BookingResponse(BaseModel):
    """Ответ на запись"""
    success: bool
    message: str
    booking_id: Optional[int] = None


class GUISettings(BaseModel):
    """Настройки GUI"""
    background_color: str = "#ffffff"
    primary_color: str = "#6366f1"
    secondary_color: str = "#8b5cf6"
    text_color: str = "#1f2937"
    calendar_style: str = "modern"  # modern, classic, minimal
    background_image: Optional[str] = None
    services: List[Service] = []  # Список услуг


class MyBooking(BaseModel):
    """Запись клиента"""
    id: int
    date: str
    time: str
    name: str
    phone: str


class AddWorkDayRequest(BaseModel):
    """Запрос на добавление рабочего дня"""
    date: str
    time_slots: list[str] | None = None


class AddTimeSlotRequest(BaseModel):
    """Запрос на добавления временного слота"""
    date: str
    time: str


class DeleteTimeSlotRequest(BaseModel):
    """Запрос на удаление временного слота"""
    date: str
    time: str


class WorkDayInfo(BaseModel):
    """Информация о рабочем дне"""
    date: str
    is_closed: bool
    slots: list[dict]  # Слоты с полями time и is_booked


class DeleteWorkDayRequest(BaseModel):
    """Запрос на удаление рабочего дня"""
    day_date: str
