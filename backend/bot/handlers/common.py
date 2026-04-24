"""
Bot command handlers:
  /start      — welcome message + Записаться button (opens Mini App)
  /cancel     — cancels active booking (FSM: ask reason → process)
  /mybooking  — shows current active booking
  /help       — shows help message
  /backup     — admin only: creates database backup
"""

import os
import subprocess
from datetime import datetime

import httpx
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

from database.db import Booking, SessionLocal, TimeSlot

router = Router()

ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
MINI_APP_URL: str = os.getenv("MINI_APP_URL", "https://temary1122-a11y.github.io/liquid-glass-calendar-design/")


# ---------------------------------------------------------------------------
# Permanent keyboard (always visible)
# ---------------------------------------------------------------------------


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записаться")],
        [KeyboardButton(text="📋 Моя запись")],
        [KeyboardButton(text="❌ Отменить запись")],
        [KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


# ---------------------------------------------------------------------------
# FSM states for /cancel flow
# ---------------------------------------------------------------------------


class CancelState(StatesGroup):
    waiting_for_reason = State()


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Главное меню с кнопкой записи через Mini App."""
    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Записаться",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Моя запись",
                    callback_data="my_booking",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись",
                    callback_data="cancel_booking",
                )
            ],
        ]
    )

    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Я помогу вам записаться к мастеру ресниц.\n\n"
        "Нажмите кнопку ниже, чтобы выбрать удобное время:",
        reply_markup=keyboard,
    )
    
    # Also show permanent keyboard
    await message.answer(
        "💡 Используйте кнопки ниже для быстрых действий:",
        reply_markup=main_keyboard,
    )


# ---------------------------------------------------------------------------
# /mybooking + callback
# ---------------------------------------------------------------------------


STATUS_EMOJI = {
    "pending": "⏳ Ожидает подтверждения",
    "confirmed": "✅ Подтверждена",
    "completed": "✅ Завершена",
    "cancelled": "❌ Отменена",
}


async def _show_booking(message: types.Message, user_id: int) -> None:
    """Показать активную запись пользователя."""
    with SessionLocal() as db:
        booking: Booking | None = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Booking.created_at.desc())
            .first()
        )

        if not booking:
            await message.answer(
                "📭 У вас нет активных записей.\n\n"
                "Используйте /start чтобы записаться."
            )
            return

        status_text = STATUS_EMOJI.get(booking.status, booking.status)

        text = (
            f"📋 <b>Ваша запись</b>\n\n"
            f"📅 Дата: <b>{booking.day_date}</b>\n"
            f"🕐 Время: <b>{booking.slot_time}</b>\n"
            f"📍 Адрес: <b>Тихий переулок, 4</b>\n"
            f"👤 Имя: {booking.client_name}\n"
            f"📞 Телефон: {booking.phone or '—'}\n\n"
            f"Статус: {status_text}\n\n"
            f"Чтобы отменить запись: /cancel"
        )

        await message.answer(text)


@router.message(Command("mybooking"))
async def cmd_mybooking(message: types.Message) -> None:
    await _show_booking(message, message.from_user.id)


@router.callback_query(F.data == "my_booking")
async def cb_my_booking(callback: types.CallbackQuery) -> None:
    await callback.answer()
    await _show_booking(callback.message, callback.from_user.id)


@router.callback_query(F.data == "cancel_booking")
async def cb_cancel_booking(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Callback handler для кнопки отмены записи."""
    await callback.answer()
    # Переиспользуем логику cmd_cancel
    with SessionLocal() as db:
        booking: Booking | None = (
            db.query(Booking)
            .filter(
                Booking.user_id == callback.from_user.id,
                Booking.status.notin_(["cancelled", "completed"]),
            )
            .first()
        )

        if not booking:
            await callback.message.answer(
                "📭 У вас нет активных записей для отмены.\n\n"
                "Используйте /start чтобы записаться."
            )
            return

        await state.set_state(CancelState.waiting_for_reason)
        await state.update_data(
            booking_id=booking.id,
            day_date=booking.day_date,
            slot_time=booking.slot_time,
        )

        await callback.message.answer(
            f"📅 <b>Ваша запись:</b>\n\n"
            f"📆 Дата: {booking.day_date}\n"
            f"⏰ Время: {booking.slot_time}\n\n"
            f"❓ <b>Почему хотите отменить?</b>\n"
            f"Напишите причину отмены:",
            parse_mode="HTML",
        )


# ---------------------------------------------------------------------------
# /cancel flow
# ---------------------------------------------------------------------------


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext) -> None:
    """Инициировать отмену записи."""
    with SessionLocal() as db:
        booking: Booking | None = (
            db.query(Booking)
            .filter(
                Booking.user_id == message.from_user.id,
                Booking.status.notin_(["cancelled", "completed"]),
            )
            .first()
        )

        if not booking:
            await message.answer(
                "📭 У вас нет активных записей для отмены.\n\n"
                "Используйте /start чтобы записаться."
            )
            return

        await state.set_state(CancelState.waiting_for_reason)
        await state.update_data(
            booking_id=booking.id,
            day_date=booking.day_date,
            slot_time=booking.slot_time,
            client_name=booking.client_name,
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена (не отменять)", callback_data="cancel_abort")]
        ]
    )

    await message.answer(
        "❓ <b>Укажите причину отмены записи:</b>\n\n"
        "(или нажмите кнопку ниже, чтобы вернуться)",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "cancel_abort", CancelState.waiting_for_reason)
async def cb_cancel_abort(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("✅ Хорошо! Ваша запись сохранена.")


@router.message(CancelState.waiting_for_reason)
async def process_cancel_reason(message: types.Message, state: FSMContext) -> None:
    """Обработать причину отмены и отменить запись."""
    reason = message.text.strip()
    data = await state.get_data()
    booking_id: int = data.get("booking_id", 0)
    day_date: str = data.get("day_date", "—")
    slot_time: str = data.get("slot_time", "—")
    client_name: str = data.get("client_name", "—")

    await state.clear()

    with SessionLocal() as db:
        booking: Booking | None = (
            db.query(Booking)
            .filter(
                Booking.id == booking_id,
                Booking.user_id == message.from_user.id,
                Booking.status.notin_(["cancelled", "completed"]),
            )
            .first()
        )

        if not booking:
            await message.answer("❌ Запись не найдена или уже отменена.")
            return

        try:
            booking.status = "cancelled"
            booking.cancelled_at = datetime.utcnow().isoformat()
            booking.cancel_reason = reason

            # Free the slot
            slot = (
                db.query(TimeSlot)
                .filter(
                    TimeSlot.day_date == booking.day_date,
                    TimeSlot.slot_time == booking.slot_time,
                )
                .first()
            )
            if slot:
                slot.is_booked = 0

            db.commit()
        except Exception as exc:
            db.rollback()
            await message.answer(f"❌ Ошибка при отмене: {exc}")
            return

    # Notify admin
    admin_text = (
        f"🔔 <b>Запись отменена</b>\n\n"
        f"👤 Имя: {client_name}\n"
        f"📅 Дата: {day_date}\n"
        f"🕐 Время: {slot_time}\n"
        f"❌ Причина: {reason}\n"
        f"🆔 Telegram: @{message.from_user.username or 'нет'}"
    )

    try:
        await message.bot.send_message(ADMIN_ID, admin_text)
    except Exception as exc:
        print(f"[bot] Failed to notify admin: {exc}")

    await message.answer(
        f"✅ <b>Запись отменена.</b>\n\n"
        f"📅 Дата: {day_date}\n"
        f"🕐 Время: {slot_time}\n\n"
        f"Для новой записи используйте /start"
    )


# ---------------------------------------------------------------------------
# /backup (admin only)
# ---------------------------------------------------------------------------


@router.message(Command("backup"))
async def cmd_backup(message: types.Message) -> None:
    """Admin only: creates database backup and sends the file."""
    # Check if user is admin
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор может использовать эту команду.")
        return

    await message.answer("⏳ Создание бекапа базы данных...\n\n⚠️ Это может занять 1-2 минуты")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.sql"

    try:
        # Get DATABASE_URL from environment
        database_url = os.getenv("DATABASE_URL", "")
        
        if not database_url:
            await message.answer("❌ DATABASE_URL не задан в переменных окружения.")
            return

        # Parse DATABASE_URL for pg_dump
        # Format: postgresql://user:password@host:port/database
        if database_url.startswith("postgresql://"):
            db_url = database_url.replace("postgresql://", "")
        else:
            db_url = database_url

        # Parse connection details
        try:
            # Extract user:password@host:port/database
            if "@" in db_url:
                auth_part, host_part = db_url.split("@", 1)
                user, password = auth_part.split(":", 1)
                
                if "/" in host_part:
                    host_port, database = host_part.split("/", 1)
                else:
                    host_port = host_part
                    database = "postgres"
                
                if ":" in host_port:
                    host, port = host_port.split(":", 1)
                else:
                    host = host_port
                    port = "5432"
            else:
                await message.answer("❌ Неверный формат DATABASE_URL")
                return

            # Run pg_dump with explicit host and port (60 second timeout)
            command = f"PGPASSWORD={password} pg_dump -h {host} -p {port} -U {user} -d {database} > {backup_filename}"
            print(f"[backup] Running command: pg_dump -h {host} -p {port} -U {user} -d {database}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            await message.answer("❌ Таймаут: бекап не создан за 60 секунд. База данных слишком большая или нет доступа.")
            return
        except Exception as parse_exc:
            await message.answer(f"❌ Ошибка парсинга DATABASE_URL: {parse_exc}")
            return

        if result.returncode == 0:
            file_size = os.path.getsize(backup_filename)
            
            # Send the backup file to admin
            with open(backup_filename, "rb") as backup_file:
                await message.answer_document(
                    document=backup_file,
                    caption=f"✅ Бекап создан: {backup_filename} ({file_size} bytes)"
                )
            
            # Clean up the backup file
            os.remove(backup_filename)
        else:
            await message.answer(f"❌ Ошибка создания бекапа: {result.stderr}")
    except Exception as exc:
        await message.answer(f"❌ Исключение при создании бекапа: {exc}")


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Показывает справку по боту."""
    help_text = (
        "📚 <b>Справка по боту</b>\n\n"
        "📅 <b>Записаться</b> — открывает календарь для записи\n"
        "📋 <b>Моя запись</b> — показывает вашу текущую запись\n"
        "❌ <b>Отменить запись</b> — отменяет вашу запись\n"
        "❓ <b>Помощь</b> — показывает эту справку\n\n"
        "💡 Используйте кнопки ниже для быстрых действий."
    )
    await message.answer(help_text, reply_markup=main_keyboard)


# ---------------------------------------------------------------------------
# Text button handlers (permanent keyboard)
# ---------------------------------------------------------------------------


@router.message(F.text == "📅 Записаться")
async def btn_book(message: types.Message) -> None:
    """Обработчик кнопки 'Записаться'."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Записаться",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "📅 Нажмите кнопку ниже для записи:",
        reply_markup=keyboard,
    )


@router.message(F.text == "📋 Моя запись")
async def btn_my_booking(message: types.Message) -> None:
    """Обработчик кнопки 'Моя запись'."""
    user_id = message.from_user.id
    await _show_booking(message, user_id)


@router.message(F.text == "❌ Отменить запись")
async def btn_cancel_booking(message: types.Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Отменить запись'."""
    user_id = message.from_user.id
    
    with SessionLocal() as db:
        booking: Booking | None = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Booking.created_at.desc())
            .first()
        )
        
        if not booking:
            await message.answer("❌ У вас нет активной записи для отмены.")
            return
        
        # Start cancel flow
        await state.update_data(booking_id=booking.id)
        await state.set_state(CancelState.waiting_for_reason)
        await message.answer(
            f"Вы уверены, что хотите отменить запись на {booking.day_date} в {booking.slot_time}?\n\n"
            "Напишите причину отмены:"
        )


@router.message(F.text == "❓ Помощь")
async def btn_help(message: types.Message) -> None:
    """Обработчик кнопки 'Помощь'."""
    await cmd_help(message)
