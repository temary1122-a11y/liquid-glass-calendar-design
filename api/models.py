# ============================================================
# api/models.py — Модели для API (используем dataclasses вместо pydantic)
# ============================================================

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TimeSlot:
    """Временной слот"""
    time: str
    available: bool


@dataclass
class WorkDay:
    """Рабочий день"""
    date: str
    slots: List[TimeSlot]
    is_closed: bool = False


@dataclass
class Service:
    """Услуга"""
    id: str
    name: str
    price: int


@dataclass
class BookingRequest:
    """Запрос на запись"""
    date: str
    time: str
    name: str
    phone: str
    service_id: str  # ID услуги


@dataclass
class BookingResponse:
    """Ответ на запись"""
    success: bool
    message: str
    booking_id: Optional[int] = None


@dataclass
class GUISettings:
    """Настройки GUI"""
    background_color: str = "#ffffff"
    primary_color: str = "#6366f1"
    secondary_color: str = "#8b5cf6"
    text_color: str = "#1f2937"
    calendar_style: str = "modern"  # modern, classic, minimal
    background_image: Optional[str] = None
    services: List[Service] = None  # Список услуг

    def __post_init__(self):
        if self.services is None:
            self.services = []


@dataclass
class MyBooking:
    """Запись клиента"""
    id: int
    date: str
    time: str
    name: str
    phone: str


@dataclass
class AddWorkDayRequest:
    """Запрос на добавление рабочего дня"""
    date: str
    time_slots: Optional[list[str]] = None


@dataclass
class AddTimeSlotRequest:
    """Запрос на добавления временного слота"""
    date: str
    time: str


@dataclass
class DeleteTimeSlotRequest:
    """Запрос на удаление временного слота"""
    date: str
    time: str


@dataclass
class WorkDayInfo:
    """Информация о рабочем дне"""
    date: str
    is_closed: bool
    slots: list[dict]  # Слоты с полями time и is_booked


@dataclass
class DeleteWorkDayRequest:
    """Запрос на удаление рабочего дня"""
    day_date: str
