"""
Bot command handlers:
  /start      — welcome message + Записаться button (opens Mini App)
  /cancel     — cancels active booking (FSM: ask reason → process)
  /mybooking  — shows current active booking
"""

import os
from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from database.db import Booking, SessionLocal

router = Router()

ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
MINI_APP_URL: str = os.getenv("MINI_APP_URL", "https://your-mini-app.vercel.app")


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
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = reason

            slot = booking.slot
            if slot:
                slot.is_booked = False

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
