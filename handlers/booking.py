# ============================================================
# handlers/booking.py — Запись клиента (FSM)
# ============================================================

import re
import logging
from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import CHANNEL_ID
from states import BookingStates
from database import (
    get_available_days,
    get_free_slots,
    create_booking,
    user_has_active_booking,
)
from keyboards import (
    main_menu_kb,
    time_slots_kb,
    confirm_booking_kb,
    cancel_confirm_kb,
    back_to_main_kb,
)
from keyboards.calendars import build_calendar
from utils import (
    notify_admin,
    post_to_schedule_channel,
    booking_text,
    admin_booking_notification,
    channel_booking_text,
    client_confirmation_text,
    format_date_ru,
)
from utils.scheduler import schedule_reminder

logger = logging.getLogger(__name__)
router = Router()

PHONE_RE = re.compile(r"^[\+\d][\d\s\-\(\)]{6,15}$")


# ────────────────────────────────────────────────────────────
# Шаг 1: Начало записи — показываем календарь
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "book_start")
async def book_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начинаем запись - показываем календарь."""
    await callback.answer()

    # Проверка: нет ли уже активной записи
    if user_has_active_booking(callback.from_user.id):
        booking = __import__("database").get_user_booking(callback.from_user.id)
        text = (
            f"⚠️ <b>У вас уже есть активная запись!</b>\n\n"
            f"📅 <b>Дата:</b> {format_date_ru(booking['day_date'])}\n"
            f"🕐 <b>Время:</b> {booking['slot_time']}\n\n"
            f"Сначала отмените текущую запись, чтобы создать новую."
        )
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_main_kb())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=back_to_main_kb())
        return

    # Получаем доступные даты
    available_rows = get_available_days()
    available_dates = {row["day_date"] for row in available_rows}

    if not available_dates:
        try:
            await callback.message.edit_text(
                "😔 <b>К сожалению, свободных мест нет.</b>\n\n"
                "Попробуйте позже или свяжитесь с мастером напрямую.",
                parse_mode="HTML",
                reply_markup=back_to_main_kb()
            )
        except Exception:
            await callback.message.answer(
                "😔 <b>К сожалению, свободных мест нет.</b>",
                parse_mode="HTML",
                reply_markup=back_to_main_kb()
            )
        return

    today = date.today()
    calendar_kb = build_calendar(available_dates, today.year, today.month)

    await state.set_state(BookingStates.choosing_date)
    await state.update_data(available_dates=list(available_dates))

    try:
        await callback.message.edit_text(
            "📅 <b>Выберите дату записи:</b>\n\n"
            "🟢 — доступные даты",
            parse_mode="HTML",
            reply_markup=calendar_kb
        )
    except Exception:
        await callback.message.answer(
            "📅 <b>Выберите дату записи:</b>",
            parse_mode="HTML",
            reply_markup=calendar_kb
        )


# ────────────────────────────────────────────────────────────
# Навигация по календарю (предыдущий / следующий месяц)
# ────────────────────────────────────────────────────────────
@router.callback_query(BookingStates.choosing_date, F.data.startswith("cal_prev:"))
@router.callback_query(BookingStates.choosing_date, F.data.startswith("cal_next:"))
async def calendar_navigate(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    available_dates = set(data.get("available_dates", []))

    _, year_str, month_str = callback.data.split(":")
    year, month = int(year_str), int(month_str)

    # Корректировка месяца
    if callback.data.startswith("cal_prev:"):
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    else:
        month += 1
        if month > 12:
            month = 1
            year += 1

    calendar_kb = build_calendar(available_dates, year, month)
    try:
        await callback.message.edit_reply_markup(reply_markup=calendar_kb)
    except Exception:
        await callback.message.edit_text(
            "📅 <b>Выберите дату записи:</b>",
            parse_mode="HTML",
            reply_markup=calendar_kb
        )


# ────────────────────────────────────────────────────────────
# Шаг 2: Выбор даты → показываем слоты
# ────────────────────────────────────────────────────────────
@router.callback_query(BookingStates.choosing_date, F.data.startswith("cal_day:"))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day_date = callback.data.split(":")[1]

    free_slots = get_free_slots(day_date)
    if not free_slots:
        await callback.answer("😔 На эту дату нет свободных слотов.", show_alert=True)
        return

    await state.update_data(selected_date=day_date)
    await state.set_state(BookingStates.choosing_time)

    await callback.message.edit_text(
        f"📅 <b>Дата:</b> {format_date_ru(day_date)}\n\n"
        f"🕐 <b>Выберите удобное время:</b>",
        parse_mode="HTML",
        reply_markup=time_slots_kb(free_slots, day_date)
    )


# ────────────────────────────────────────────────────────────
# Шаг 3: Выбор времени → запрашиваем имя
# ────────────────────────────────────────────────────────────
@router.callback_query(BookingStates.choosing_time, F.data.startswith("slot:"))
async def slot_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    day_date = parts[1]
    slot_time = parts[2]

    await state.update_data(selected_date=day_date, selected_time=slot_time)
    await state.set_state(BookingStates.entering_name)

    await callback.message.edit_text(
        f"📅 <b>{format_date_ru(day_date)}</b> в <b>{slot_time}</b>\n\n"
        f"👤 Введите ваше <b>имя</b>:",
        parse_mode="HTML",
    )


# ────────────────────────────────────────────────────────────
# Шаг 4: Ввод имени → запрашиваем телефон
# ────────────────────────────────────────────────────────────
@router.message(BookingStates.entering_name, F.text)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer("⚠️ Пожалуйста, введите корректное имя (2–60 символов).")
        return

    await state.update_data(client_name=name)
    await state.set_state(BookingStates.entering_phone)

    await message.answer(
        f"✅ <b>Имя:</b> {name}\n\n"
        f"📞 Введите ваш <b>номер телефона</b>:\n"
        f"<i>(например: +7 900 123-45-67)</i>",
        parse_mode="HTML"
    )


# ────────────────────────────────────────────────────────────
# Шаг 5: Ввод телефона → показываем подтверждение
# ────────────────────────────────────────────────────────────
@router.message(BookingStates.entering_phone, F.text)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_RE.match(phone):
        await message.answer(
            "⚠️ Некорректный номер телефона.\n"
            "Введите номер в формате: <code>+7 900 123-45-67</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    await state.update_data(phone=phone)
    await state.set_state(BookingStates.confirming)

    confirmation_text = (
        f"📋 <b>Проверьте данные записи:</b>\n\n"
        f"👤 <b>Имя:</b> {data['client_name']}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"📅 <b>Дата:</b> {format_date_ru(data['selected_date'])}\n"
        f"🕐 <b>Время:</b> {data['selected_time']}\n\n"
        f"Всё верно?"
    )
    await message.answer(
        confirmation_text,
        parse_mode="HTML",
        reply_markup=confirm_booking_kb()
    )


# ────────────────────────────────────────────────────────────
# Шаг 6: Подтверждение → сохраняем запись
# ────────────────────────────────────────────────────────────
@router.callback_query(BookingStates.confirming, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()

    booking_id = create_booking(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        client_name=data["client_name"],
        phone=data["phone"],
        day_date=data["selected_date"],
        slot_time=data["selected_time"],
    )

    if booking_id is None:
        await callback.message.edit_text(
            "😔 <b>К сожалению, этот слот уже занят.</b>\n\n"
            "Попробуйте выбрать другое время.",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
        await state.clear()
        return

    await state.clear()

    # ── Сообщение пользователю с новым форматом ───────────────
    await callback.message.edit_text(
        client_confirmation_text(
            day_date=data["selected_date"],
            slot_time=data["selected_time"],
        ),
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )

    # ── Уведомление администратору ────────────────────────────
    await notify_admin(
        bot,
        admin_booking_notification(
            client_name=data["client_name"],
            phone=data["phone"],
            day_date=data["selected_date"],
            slot_time=data["selected_time"],
            username=callback.from_user.username,
            user_id=callback.from_user.id,
            booking_id=booking_id,
        )
    )

    # ── Публикация в канал расписания ─────────────────────────
    await post_to_schedule_channel(
        bot,
        channel_booking_text(
            client_name=data["client_name"],
            day_date=data["selected_date"],
            slot_time=data["selected_time"],
            booking_id=booking_id,
        )
    )

    # ── Планирование напоминания ──────────────────────────────
    schedule_reminder(
        bot=bot,
        booking_id=booking_id,
        user_id=callback.from_user.id,
        day_date=data["selected_date"],
        slot_time=data["selected_time"],
    )


# ────────────────────────────────────────────────────────────
# Отмена процесса бронирования (кнопка «Отмена» на шаге подтверждения)
# ────────────────────────────────────────────────────────────
@router.callback_query(BookingStates.confirming, F.data == "cancel_booking_process")
async def cancel_booking_process(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(
            "❌ <b>Запись отменена.</b>\n\nВы можете начать сначала.",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            "❌ <b>Запись отменена.</b>",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Отмена своей записи пользователем
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_start(callback: CallbackQuery):
    from database import get_user_booking
    await callback.answer()
    booking = get_user_booking(callback.from_user.id)
    if not booking:
        try:
            await callback.message.edit_text(
                "📭 <b>У вас нет активных записей.</b>",
                parse_mode="HTML",
                reply_markup=back_to_main_kb()
            )
        except Exception:
            await callback.message.answer(
                "📭 <b>У вас нет активных записей.</b>",
                parse_mode="HTML",
                reply_markup=back_to_main_kb()
            )
        return

    text = (
        f"⚠️ <b>Вы действительно хотите отменить запись?</b>\n\n"
        f"📅 <b>Дата:</b> {format_date_ru(booking['day_date'])}\n"
        f"🕐 <b>Время:</b> {booking['slot_time']}\n"
        f"👤 <b>Имя:</b> {booking['client_name']}"
    )
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=cancel_confirm_kb()
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=cancel_confirm_kb()
        )


@router.callback_query(F.data == "do_cancel_booking")
async def do_cancel_booking(callback: CallbackQuery, bot: Bot):
    from database import cancel_booking_by_user, get_user_booking
    from utils.scheduler import cancel_reminder
    await callback.answer()

    # Получаем данные до отмены (нужен booking_id для напоминания)
    booking_before = get_user_booking(callback.from_user.id)
    cancelled = cancel_booking_by_user(callback.from_user.id)

    if cancelled is None:
        try:
            await callback.message.edit_text(
                "📭 Нет активных записей для отмены.",
                reply_markup=back_to_main_kb()
            )
        except Exception:
            await callback.message.answer("📭 Нет активных записей для отмены.")
        return

    # Удаляем напоминание
    if booking_before:
        cancel_reminder(booking_before["id"])

    # Уведомляем администратора
    await notify_admin(
        bot,
        f"🔴 <b>Запись отменена клиентом</b>\n\n"
        f"👤 {cancelled['client_name']}\n"
        f"📞 {cancelled['phone']}\n"
        f"📅 {format_date_ru(cancelled['day_date'])} в {cancelled['slot_time']}"
    )

    try:
        await callback.message.edit_text(
            f"✅ <b>Ваша запись успешно отменена.</b>\n\n"
            f"📅 {format_date_ru(cancelled['day_date'])} в {cancelled['slot_time']}\n\n"
            f"Будем рады видеть вас снова! 💅",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            "✅ <b>Запись отменена.</b>",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
