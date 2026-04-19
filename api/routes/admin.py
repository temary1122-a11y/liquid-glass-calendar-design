# ============================================================
# api/routes/admin.py — Routes для админки
# ============================================================

from fastapi import APIRouter, HTTPException, Header, Request
from slowapi import Limiter
from api.models import (
    GUISettings,
    Service,
    AddWorkDayRequest,
    AddTimeSlotRequest,
    DeleteTimeSlotRequest,
    DeleteWorkDayRequest,
    WorkDayInfo,
    AdminClientRequest,
    DeleteClientRequest,
)
from database.db import (
    add_work_day,
    add_time_slot,
    delete_time_slot,
    delete_work_day,
    get_all_slots,
    get_all_work_days,
    close_day,
    open_day,
    create_booking,
    update_booking,
    delete_booking,
    get_bookings_for_day,
)
from config import ADMIN_ID

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Rate limiter instance
limiter = Limiter(key_func=lambda r: r.client.host if r.client else r.headers.get("x-forwarded-for", ""))

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


async def verify_admin(x_admin_id: int = Header(None, description="Admin ID for authentication")):
    """Проверка админ-прав"""
    if x_admin_id != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Access denied")


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
async def add_work_day_endpoint(request: Request, body: dict, x_admin_id: int = Header(None)):
    """Добавить рабочий день"""
    await verify_admin(x_admin_id)
    print(f"DEBUG add-work-day: body={body}, x_admin_id={x_admin_id}")

    date = body.get("date")
    time_slots = body.get("time_slots")

    if not date:
        raise HTTPException(status_code=422, detail="date is required")

    if not time_slots:
        raise HTTPException(status_code=422, detail="time_slots is required")

    success = add_work_day(date, time_slots)
    if success:
        return {"success": True, "message": "Рабочий день добавлен"}
    else:
        return {"success": False, "message": "День уже существует"}


@router.post("/add-time-slot")
@limiter.limit("200/minute")
async def add_time_slot_endpoint(request: Request, body: AddTimeSlotRequest, x_admin_id: int = Header(None)):
    """Добавить временной слот"""
    await verify_admin(x_admin_id)
    print(f"DEBUG add-time-slot: body={body}, x_admin_id={x_admin_id}")

    success = add_time_slot(body.date, body.time)
    if success:
        return {"success": True, "message": "Слот добавлен"}
    else:
        return {"success": False, "message": "Слот уже существует или день не найден"}


@router.post("/delete-time-slot")
@limiter.limit("200/minute")
async def delete_time_slot_endpoint(request: Request, body: DeleteTimeSlotRequest, x_admin_id: int = Header(None)):
    """Удалить временной слот"""
    await verify_admin(x_admin_id)
    print(f"DEBUG delete-time-slot: body={body}, x_admin_id={x_admin_id}")

    success = delete_time_slot(body.date, body.time)
    if success:
        return {"success": True, "message": "Слот удалён"}
    else:
        return {"success": False, "message": "Слот занят или не найден"}


@router.get("/work-days", response_model=list[WorkDayInfo])
@limiter.limit("200/minute")
async def get_work_days_endpoint(request: Request, x_admin_id: int = Header(None)):
    """Получить все рабочие дни"""
    await verify_admin(x_admin_id)

    work_days = get_all_work_days()
    result = []
    for day in work_days:
        slots = get_all_slots(day[1])  # day[1] = day_date
        # Формируем слоты с полной информацией
        slot_info = []
        for slot in slots:
            slot_info.append({
                'time': slot[2],  # slot_time
                'is_booked': bool(slot[3])  # is_booked
            })
        result.append(
            WorkDayInfo(
                date=day[1],
                is_closed=bool(day[2]),
                slots=slot_info,
            )
        )
    return result


@router.get("/bookings/{date}")
@limiter.limit("200/minute")
async def get_bookings_for_date(request: Request, date: str, x_admin_id: int = Header(None)):
    """Получить записи на конкретную дату"""
    await verify_admin(x_admin_id)

    from database.db import get_conn

    with get_conn() as conn:
        bookings = conn.execute(
            """SELECT id, user_id, username, client_name, phone, day_date, slot_time, service_id
               FROM bookings WHERE day_date = ? ORDER BY slot_time""",
            (date,)
        ).fetchall()

        result = []
        for booking in bookings:
            result.append({
                'id': booking[0],
                'user_id': booking[1],
                'username': booking[2],
                'client_name': booking[3],
                'phone': booking[4],
                'day_date': booking[5],
                'slot_time': booking[6],
                'service_id': booking[7],
            })

        return result


@router.post("/close-day")
@limiter.limit("200/minute")
async def close_day_endpoint(request: Request, body: dict, x_admin_id: int = Header(None)):
    """Закрыть рабочий день"""
    await verify_admin(x_admin_id)
    date = body.get("date")
    if not date:
        raise HTTPException(status_code=422, detail="date is required")
    close_day(date)
    return {"success": True, "message": "День закрыт"}


@router.post("/open-day")
@limiter.limit("200/minute")
async def open_day_endpoint(request: Request, body: dict, x_admin_id: int = Header(None)):
    """Открыть рабочий день"""
    await verify_admin(x_admin_id)
    date = body.get("date")
    if not date:
        raise HTTPException(status_code=422, detail="date is required")
    open_day(date)
    return {"success": True, "message": "День открыт"}


@router.post("/delete-work-day")
@limiter.limit("200/minute")
async def delete_work_day_endpoint(request: Request, body: DeleteWorkDayRequest, x_admin_id: int = Header(None)):
    """Удалить рабочий день"""
    await verify_admin(x_admin_id)
    success = delete_work_day(body.day_date)
    if success:
        return {"success": True, "message": "Рабочий день удалён"}
    else:
        return {"success": False, "message": "Рабочий день не найден"}


@router.post("/cleanup-database")
@limiter.limit("10/hour", key_func=lambda: "cleanup")
async def cleanup_database_endpoint(request: Request, x_admin_id: int = Header(None)):
    """Полностью очистить базу данных"""
    await verify_admin(x_admin_id)

    from database.db import get_conn

    with get_conn() as conn:
        cursor = conn.cursor()

        # Удаляем все данные
        cursor.execute("DELETE FROM bookings")
        deleted_bookings = cursor.rowcount

        cursor.execute("DELETE FROM time_slots")
        deleted_slots = cursor.rowcount

        cursor.execute("DELETE FROM work_days")
        deleted_work_days = cursor.rowcount

        conn.commit()

    return {
        "success": True,
        "deleted_bookings": deleted_bookings,
        "deleted_slots": deleted_slots,
        "deleted_work_days": deleted_work_days,
        "message": "База данных полностью очищена"
    }


@router.post("/create-client")
@limiter.limit("200/minute")
async def create_client_endpoint(request: Request, body: AdminClientRequest, x_admin_id: int = Header(None)):
    """Создать запись клиента через админ панель"""
    await verify_admin(x_admin_id)
    print(f"DEBUG create-client: body={body}, x_admin_id={x_admin_id}")

    # Создаем запись с user_id=0 если это ручная запись
    user_id = body.user_id if body.user_id else 0
    booking = create_booking(
        user_id=user_id,
        username=body.username,
        client_name=body.name,
        phone=body.phone,
        day_date=body.date,
        slot_time=body.time,
        service_id="manual",  # Ручная запись
    )

    if booking:
        return {"success": True, "message": "Клиент добавлен", "booking_id": booking["id"]}
    else:
        return {"success": False, "message": "Не удалось добавить клиента"}


@router.post("/update-client")
@limiter.limit("200/minute")
async def update_client_endpoint(request: Request, body: AdminClientRequest, x_admin_id: int = Header(None)):
    """Обновить запись клиента через админ панель"""
    await verify_admin(x_admin_id)
    print(f"DEBUG update-client: body={body}, x_admin_id={x_admin_id}")

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


@router.post("/delete-client")
@limiter.limit("200/minute")
async def delete_client_endpoint(request: Request, body: DeleteClientRequest, x_admin_id: int = Header(None)):
    """Удалить запись клиента через админ панель"""
    await verify_admin(x_admin_id)
    print(f"DEBUG delete-client: body={body}, x_admin_id={x_admin_id}")

    success = delete_booking(body.date, body.time)
    if success:
        return {"success": True, "message": "Клиент удален"}
    else:
        return {"success": False, "message": "Клиент не найден"}
