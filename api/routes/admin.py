# ============================================================
# api/routes/admin.py — Routes для админки
# ============================================================

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from slowapi import Limiter
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)

from api.models import (
    GUISettings,
    Service,
    AddWorkDayRequest,
    AddTimeSlotRequest,
    DeleteTimeSlotRequest,
    DeleteWorkDayRequest,
    WorkDayInfo,
    AdminClientRequest,
    UpdateSlotTimeRequest,
    DeleteClientRequest,
    MarkBookingCompletedRequest,
)
from database.db import (
    add_work_day,
    add_time_slot,
    delete_time_slot,
    delete_work_day,
    get_all_slots,
    get_all_work_days,
    get_work_days_with_slots,
    get_work_days_with_bookings,
    close_day,
    open_day,
    create_booking,
    update_slot_time,
    update_booking,
    delete_booking,
    get_bookings_for_day,
    mark_booking_completed,
)
from config import ADMIN_ID, ADMIN_SECRET_KEY
from api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Rate limiter instance
def get_key_func(r=None):
    return "default"

limiter = Limiter(key_func=get_key_func)

# Временное хранилище настроек (в продакшене — в БД)
gui_settings = GUISettings(
    services=[
        Service(id="classic", name="Классические ресницы", price=2000),
        Service(id="volume", name="Объемные ресницы", price=3000),
        Service(id="2d", name="2D эффект", price=3500),
        Service(id="3d", name="3D эффект", price=4000),
        Service(id="removal", name="Снятие ресниц", price=500),
    ]
)


async def verify_admin(
    request: Request,
    x_admin_id: int = Header(None, description="Admin ID for authentication"),
    x_admin_signature: str = Header(None, description="Admin HMAC signature (optional)")
):
    """Проверка админ-прав - базовая защита через admin_id"""
    client_host = request.client.host if request.client else 'unknown'

    if x_admin_id is None:
        logger.warning(f"Missing admin ID from {client_host}")
        raise HTTPException(status_code=403, detail="Missing admin ID")

    if x_admin_id != ADMIN_ID:
        logger.warning(f"Invalid admin ID: {x_admin_id} from {client_host}")
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"Admin authenticated successfully from {client_host}")
    return x_admin_id


@router.get("/settings", response_model=GUISettings)
@limiter.limit("200/minute")
async def get_gui_settings(request: Request):
    """Получить настройки GUI"""
    return gui_settings


@router.post("/settings", response_model=GUISettings)
@limiter.limit("200/minute")
async def update_gui_settings(request: Request, settings: GUISettings):
    """Обновить настройки GUI"""
    global gui_settings
    gui_settings = settings

    # В продакшене здесь будет сохранение в БД
    # save_gui_settings_to_db(settings)

    return gui_settings


@router.post("/add-work-day")
@limiter.limit("200/minute")
async def add_work_day_endpoint(request: Request, body: dict, admin_id: int = Depends(verify_admin)):
    """Добавить рабочий день"""
    print(f"DEBUG add-work-day: body={body}, admin_id={admin_id}")

    date = body.get("date")
    time_slots = body.get("time_slots")

    if not date:
        raise HTTPException(status_code=422, detail="date is required")

    if not time_slots:
        raise HTTPException(status_code=422, detail="time_slots is required")

    success = add_work_day(date, time_slots)
    if success:
        # Broadcast slot update to all connected clients
        await manager.send_slot_update(
            event_type="added",
            slot_data={"date": date, "time_slots": time_slots}
        )
        return {"success": True, "message": "Рабочий день добавлен"}
    else:
        return {"success": False, "message": "День уже существует"}


@router.post("/add-time-slot")
@limiter.limit("200/minute")
async def add_time_slot_endpoint(request: Request, body: AddTimeSlotRequest, admin_id: int = Depends(verify_admin)):
    """Добавить временной слот"""
    print(f"DEBUG add-time-slot: body={body}, admin_id={admin_id}")

    success = add_time_slot(body.date, body.time)
    if success:
        return {"success": True, "message": "Слот добавлен"}
    else:
        return {"success": False, "message": "Слот уже существует или день не найден"}


@router.post("/delete-time-slot")
@limiter.limit("200/minute")
async def delete_time_slot_endpoint(request: Request, body: DeleteTimeSlotRequest, admin_id: int = Depends(verify_admin)):
    """Удалить временной слот"""
    print(f"DEBUG delete-time-slot: body={body}, admin_id={admin_id}")

    success = delete_time_slot(body.date, body.time)
    if success:
        return {"success": True, "message": "Слот удалён"}
    else:
        return {"success": False, "message": "Слот занят или не найден"}


@router.get("/work-days", response_model=list[WorkDayInfo])
@limiter.limit("200/minute")
async def get_work_days_endpoint(request: Request, admin_id: int = Depends(verify_admin)):
    """Получить все рабочие дни (оптимизировано - один запрос вместо N+1)"""

    work_days = get_work_days_with_slots()
    result = []
    for day in work_days:
        result.append(
            WorkDayInfo(
                date=day["day_date"],
                is_closed=bool(day["is_closed"]),
                slots=day["slots"],
            )
        )
    return result


@router.get("/work-days-with-bookings")
@limiter.limit("200/minute")
async def get_work_days_with_bookings_endpoint(request: Request, admin_id: int = Depends(verify_admin)):
    """Получить все рабочие дни со слотами и bookings за один запрос"""
    return get_work_days_with_bookings()


@router.get("/bookings/{date}")
@limiter.limit("200/minute")
async def get_bookings_for_date(request: Request, date: str, admin_id: int = Depends(verify_admin)):
    """Получить записи на конкретную дату"""

    from database.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """SELECT id, user_id, username, client_name, phone, day_date, slot_time, service_id
               FROM bookings WHERE day_date = ? ORDER BY slot_time""",
            (date,)
        )
        bookings = conn.fetchall()

        result = []
        for booking in bookings:
            result.append({
                'id': booking["id"],
                'user_id': booking["user_id"],
                'username': booking["username"],
                'client_name': booking["client_name"],
                'phone': booking["phone"],
                'day_date': booking["day_date"],
                'slot_time': booking["slot_time"],
                'service_id': booking["service_id"],
            })

        return result


@router.post("/close-day")
@limiter.limit("200/minute")
async def close_day_endpoint(request: Request, body: dict, admin_id: int = Depends(verify_admin)):
    """Закрыть рабочий день"""
    date = body.get("date")
    if not date:
        raise HTTPException(status_code=422, detail="date is required")
    close_day(date)
    return {"success": True, "message": "День закрыт"}


@router.post("/open-day")
@limiter.limit("200/minute")
async def open_day_endpoint(request: Request, body: dict, admin_id: int = Depends(verify_admin)):
    """Открыть рабочий день"""
    date = body.get("date")
    if not date:
        raise HTTPException(status_code=422, detail="date is required")
    open_day(date)
    return {"success": True, "message": "День открыт"}


@router.post("/delete-work-day")
@limiter.limit("200/minute")
async def delete_work_day_endpoint(request: Request, body: DeleteWorkDayRequest, admin_id: int = Depends(verify_admin)):
    """Удалить рабочий день"""
    success = delete_work_day(body.day_date)
    if success:
        return {"success": True, "message": "Рабочий день удалён"}
    else:
        return {"success": False, "message": "Рабочий день не найден"}


@router.post("/cleanup-database")
@limiter.limit("10/hour", key_func=lambda r: "cleanup")
async def cleanup_database_endpoint(request: Request, admin_id: int = Depends(verify_admin)):
    """Полностью очистить базу данных"""

    from database.db import get_conn

    with get_conn() as conn:
        # Удаляем все данные
        conn.execute("DELETE FROM bookings")
        deleted_bookings = conn.rowcount

        conn.execute("DELETE FROM time_slots")
        deleted_slots = conn.rowcount

        conn.execute("DELETE FROM work_days")
        deleted_work_days = conn.rowcount

    return {
        "success": True,
        "deleted_bookings": deleted_bookings,
        "deleted_slots": deleted_slots,
        "deleted_work_days": deleted_work_days,
        "message": "База данных полностью очищена"
    }


@router.post("/create-client")
@limiter.limit("200/minute")
async def create_client_endpoint(request: Request, body: AdminClientRequest, admin_id: int = Depends(verify_admin)):
    """Создать запись клиента через админ панель"""
    print(f"DEBUG create-client: body={body}, admin_id={admin_id}")

    # Создаем запись с user_id=0 если это ручная запись
    user_id = body.user_id if body.user_id else 0
    booking_id = create_booking(
        user_id=user_id,
        username=body.username,
        client_name=body.name,
        phone=body.phone,
        day_date=body.date,
        slot_time=body.time,
        service_id="manual",  # Ручная запись
    )

    if booking_id:
        return {"success": True, "message": "Клиент добавлен", "booking_id": booking_id}
    else:
        return {"success": False, "message": "Не удалось добавить клиента"}


@router.post("/update-client")
@limiter.limit("200/minute")
async def update_client_endpoint(request: Request, body: AdminClientRequest, admin_id: int = Depends(verify_admin)):
    """Обновить запись клиента через админ панель"""
    print(f"DEBUG update-client: body={body}, admin_id={admin_id}")

    # Находим существующую запись
    existing_bookings = get_bookings_for_day(body.date)
    existing_booking = None
    for booking in existing_bookings:
        if booking["slot_time"] == body.time:
            existing_booking = booking
            break

    if not existing_booking:
        return {"success": False, "message": "Запись не найдена"}

    # Обновляем запись
    updated = update_booking(
        booking_id=existing_booking["id"],
        client_name=body.name,
        phone=body.phone,
        day_date=body.date,
        slot_time=body.time,
        username=body.username,
        note=body.note,
    )

    if updated:
        return {"success": True, "message": "Клиент обновлен"}
    else:
        return {"success": False, "message": "Не удалось обновить клиента"}


@router.post("/update-slot-time")
@limiter.limit("200/minute")
async def update_slot_time_endpoint(request: Request, body: UpdateSlotTimeRequest, admin_id: int = Depends(verify_admin)):
    """Обновить время слота (для редактирования пустого слота без клиента)"""
    print(f"DEBUG update-slot-time: body={body}, admin_id={admin_id}")

    success = update_slot_time(
        old_date=body.old_date,
        old_time=body.old_time,
        new_date=body.new_date,
        new_time=body.new_time,
    )

    if success:
        return {"success": True, "message": "Время слота обновлено"}
    else:
        return {"success": False, "message": "Не удалось обновить время слота"}


@router.post("/mark-booking-completed")
@limiter.limit("200/minute")
async def mark_booking_completed_endpoint(request: Request, body: MarkBookingCompletedRequest, admin_id: int = Depends(verify_admin)):
    """Пометить запись как исполненную (completed)"""
    print(f"DEBUG mark-booking-completed: body={body}, admin_id={admin_id}")

    success = mark_booking_completed(body.booking_id)

    if success:
        return {"success": True, "message": "Запись помечена как исполненная"}
    else:
        return {"success": False, "message": "Не удалось пометить запись как исполненную"}


@router.post("/delete-client")
@limiter.limit("200/minute")
async def delete_client_endpoint(request: Request, body: DeleteClientRequest, admin_id: int = Depends(verify_admin)):
    """Удалить запись клиента через админ панель"""
    print(f"DEBUG delete-client: body={body}, admin_id={admin_id}")

    success = delete_booking(body.date, body.time)
    if success:
        return {"success": True, "message": "Клиент удален"}
    else:
        return {"success": False, "message": "Клиент не найден"}
