# ============================================================
# handlers/admin.py — Полная админ-панель (FSM)
# ============================================================

import logging
import re
from datetime import date, datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from config import ADMIN_ID, DEFAULT_TIME_SLOTS
from states import AdminStates
from database import (
    add_work_day, close_day, open_day,
    get_all_work_days, get_free_slots, get_all_slots,
    add_time_slot, delete_time_slot,
    cancel_booking_by_id, get_bookings_for_day,
    get_all_future_bookings, day_exists,
)
from keyboards import (
    admin_menu_kb, back_to_main_kb,
    admin_slots_delete_kb, admin_bookings_kb, yes_no_kb,
)
from keyboards.calendars import build_admin_calendar
from utils import format_date_ru, notify_admin
from utils.scheduler import cancel_reminder

logger = logging.getLogger(__name__)
router = Router()

# Фильтр: только администратор
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ────────────────────────────────────────────────────────────
# Защита: отклоняем не-админов
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_menu")
async def admin_menu_cb(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(
            "🔧 <b>Панель администратора</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            "🔧 <b>Панель администратора</b>",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Просмотр расписания на день
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_view_schedule")
async def adm_view_schedule_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.choosing_day_view)

    work_days = get_all_work_days()
    all_dates = {row["day_date"] for row in work_days}
    today = date.today()
    calendar_kb = build_admin_calendar(all_dates, today.year, today.month)

    try:
        await callback.message.edit_text(
            "📅 <b>Выберите день для просмотра расписания:</b>",
            parse_mode="HTML",
            reply_markup=calendar_kb
        )
    except Exception:
        await callback.message.answer(
            "📅 <b>Выберите день:</b>",
            parse_mode="HTML",
            reply_markup=calendar_kb
        )


@router.callback_query(AdminStates.choosing_day_view, F.data.startswith("adm_day:"))
async def adm_view_day(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day_date = callback.data.split(":")[1]

    slots = get_all_slots(day_date)
    bookings = get_bookings_for_day(day_date)

    # Формируем таблицу расписания
    lines = [f"📅 <b>Расписание на {format_date_ru(day_date)}</b>\n"]
    if not slots:
        lines.append("Нет слотов.")
    else:
        bookings_map = {b["slot_time"]: b for b in bookings}
        for slot in slots:
            t = slot["slot_time"]
            if t in bookings_map:
                b = bookings_map[t]
                lines.append(f"🔴 <b>{t}</b> — {b['client_name']} ({b['phone']})")
            else:
                lines.append(f"🟢 <b>{t}</b> — свободно")

    await state.clear()
    try:
        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ── Навигация по админ-календарю ─────────────────────────────
@router.callback_query(
    StateFilter(
        AdminStates.choosing_day_view,
        AdminStates.choosing_day_to_close,
        AdminStates.choosing_day_to_open,
        AdminStates.choosing_day_add_slot,
        AdminStates.choosing_day_del_slot,
    ),
    F.data.startswith("adm_cal_prev:")
)
@router.callback_query(
    StateFilter(
        AdminStates.choosing_day_view,
        AdminStates.choosing_day_to_close,
        AdminStates.choosing_day_to_open,
        AdminStates.choosing_day_add_slot,
        AdminStates.choosing_day_del_slot,
    ),
    F.data.startswith("adm_cal_next:")
)
async def adm_calendar_navigate(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, year_str, month_str = callback.data.split(":")
    year, month = int(year_str), int(month_str)

    if callback.data.startswith("adm_cal_prev:"):
        month -= 1
        if month < 1:
            month, year = 12, year - 1
    else:
        month += 1
        if month > 12:
            month, year = 1, year + 1

    work_days = get_all_work_days()
    all_dates = {row["day_date"] for row in work_days}
    calendar_kb = build_admin_calendar(all_dates, year, month)
    try:
        await callback.message.edit_reply_markup(reply_markup=calendar_kb)
    except Exception:
        pass


# ── Пустой день (для добавления) ─────────────────────────────
@router.callback_query(
    StateFilter(AdminStates.choosing_day_to_close),
    F.data.startswith("adm_empty_day:")
)
async def adm_empty_day_close(callback: CallbackQuery):
    await callback.answer("Этот день не является рабочим.", show_alert=True)


@router.callback_query(
    StateFilter(AdminStates.choosing_day_to_open),
    F.data.startswith("adm_empty_day:")
)
async def adm_empty_day_open(callback: CallbackQuery):
    await callback.answer("Этот день не является рабочим.", show_alert=True)


@router.callback_query(
    StateFilter(AdminStates.choosing_day_add_slot),
    F.data.startswith("adm_empty_day:")
)
async def adm_empty_day_slot(callback: CallbackQuery):
    await callback.answer("Этот день не является рабочим.", show_alert=True)


@router.callback_query(
    StateFilter(AdminStates.choosing_day_del_slot),
    F.data.startswith("adm_empty_day:")
)
async def adm_empty_day_del(callback: CallbackQuery):
    await callback.answer("Этот день не является рабочим.", show_alert=True)


@router.callback_query(
    StateFilter(AdminStates.choosing_day_view),
    F.data.startswith("adm_empty_day:")
)
async def adm_empty_day_view(callback: CallbackQuery):
    await callback.answer("Нет данных для этого дня.", show_alert=True)


# ────────────────────────────────────────────────────────────
# Добавить рабочий день
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_add_day")
async def adm_add_day_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.add_day_input)

    try:
        await callback.message.edit_text(
            "📅 <b>Введите дату рабочего дня</b> в формате <code>ГГГГ-ММ-ДД</code>:\n\n"
            "<i>Например: 2025-07-15</i>",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "📅 <b>Введите дату</b> (ГГГГ-ММ-ДД):",
            parse_mode="HTML",
        )


@router.message(AdminStates.add_day_input, F.text)
async def adm_add_day_date(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    date_str = message.text.strip()
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        if d < date.today():
            await message.answer("⚠️ Нельзя добавить прошедшую дату. Введите будущую дату:")
            return
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите дату в формате <code>ГГГГ-ММ-ДД</code>:", parse_mode="HTML")
        return

    await state.update_data(new_day_date=date_str)
    await state.set_state(AdminStates.add_day_slots)

    default_slots_str = ", ".join(DEFAULT_TIME_SLOTS)
    await message.answer(
        f"✅ <b>Дата:</b> {format_date_ru(date_str)}\n\n"
        f"🕐 Введите временные слоты через запятую:\n"
        f"<i>По умолчанию: {default_slots_str}</i>\n\n"
        f"Или отправьте <code>default</code> для использования стандартных слотов.",
        parse_mode="HTML"
    )


@router.message(AdminStates.add_day_slots, F.text)
async def adm_add_day_slots(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    day_date = data["new_day_date"]
    text = message.text.strip()

    if text.lower() == "default":
        slots = DEFAULT_TIME_SLOTS
    else:
        raw = [s.strip() for s in text.split(",")]
        time_pattern = re.compile(r"^\d{2}:\d{2}$")
        slots = []
        for s in raw:
            if time_pattern.match(s):
                slots.append(s)
            else:
                await message.answer(
                    f"⚠️ Некорректное время: <code>{s}</code>.\n"
                    f"Формат: <code>ЧЧ:ММ</code>, слоты через запятую.",
                    parse_mode="HTML"
                )
                return

    success = add_work_day(day_date, slots)
    await state.clear()

    if success:
        await message.answer(
            f"✅ <b>Рабочий день добавлен!</b>\n\n"
            f"📅 {format_date_ru(day_date)}\n"
            f"🕐 Слоты: {', '.join(slots)}",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    else:
        await message.answer(
            f"⚠️ День <b>{format_date_ru(day_date)}</b> уже существует.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Закрыть рабочий день
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_close_day")
async def adm_close_day_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.choosing_day_to_close)

    work_days = get_all_work_days()
    all_dates = {row["day_date"] for row in work_days}
    today = date.today()

    try:
        await callback.message.edit_text(
            "🔒 <b>Выберите день для закрытия:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )
    except Exception:
        await callback.message.answer(
            "🔒 <b>Выберите день:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )


@router.callback_query(AdminStates.choosing_day_to_close, F.data.startswith("adm_day:"))
async def adm_close_day_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day_date = callback.data.split(":")[1]
    close_day(day_date)
    await state.clear()
    try:
        await callback.message.edit_text(
            f"🔒 <b>День {format_date_ru(day_date)} закрыт.</b>\n"
            f"Все слоты недоступны для записи.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            f"🔒 День {format_date_ru(day_date)} закрыт.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Открыть рабочий день
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_open_day")
async def adm_open_day_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.choosing_day_to_open)

    work_days = get_all_work_days()
    all_dates = {row["day_date"] for row in work_days}
    today = date.today()

    try:
        await callback.message.edit_text(
            "🔓 <b>Выберите день для открытия:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )
    except Exception:
        await callback.message.answer(
            "🔓 <b>Выберите день:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )


@router.callback_query(AdminStates.choosing_day_to_open, F.data.startswith("adm_day:"))
async def adm_open_day_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day_date = callback.data.split(":")[1]
    open_day(day_date)
    await state.clear()
    try:
        await callback.message.edit_text(
            f"🔓 <b>День {format_date_ru(day_date)} открыт.</b>",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            f"🔓 День {format_date_ru(day_date)} открыт.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Добавить временной слот
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_add_slot")
async def adm_add_slot_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.choosing_day_add_slot)

    work_days = get_all_work_days()
    all_dates = {row["day_date"] for row in work_days}
    today = date.today()

    try:
        await callback.message.edit_text(
            "➕ <b>Выберите день для добавления слота:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )
    except Exception:
        await callback.message.answer(
            "➕ <b>Выберите день:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )


@router.callback_query(AdminStates.choosing_day_add_slot, F.data.startswith("adm_day:"))
async def adm_add_slot_day(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day_date = callback.data.split(":")[1]
    await state.update_data(target_day=day_date)
    await state.set_state(AdminStates.add_slot_time_input)

    await callback.message.edit_text(
        f"📅 <b>{format_date_ru(day_date)}</b>\n\n"
        f"🕐 Введите время нового слота в формате <code>ЧЧ:ММ</code>:\n"
        f"<i>Например: 11:00</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.add_slot_time_input, F.text)
async def adm_add_slot_time(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    slot_time = message.text.strip()
    if not re.match(r"^\d{2}:\d{2}$", slot_time):
        await message.answer("⚠️ Неверный формат. Введите время как <code>ЧЧ:ММ</code>:", parse_mode="HTML")
        return

    data = await state.get_data()
    day_date = data["target_day"]
    success = add_time_slot(day_date, slot_time)
    await state.clear()

    if success:
        await message.answer(
            f"✅ Слот <b>{slot_time}</b> добавлен на {format_date_ru(day_date)}.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    else:
        await message.answer(
            f"⚠️ Слот <b>{slot_time}</b> уже существует на {format_date_ru(day_date)}.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Удалить временной слот
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_del_slot")
async def adm_del_slot_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.choosing_day_del_slot)

    work_days = get_all_work_days()
    all_dates = {row["day_date"] for row in work_days}
    today = date.today()

    try:
        await callback.message.edit_text(
            "🗑 <b>Выберите день для удаления слота:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )
    except Exception:
        await callback.message.answer(
            "🗑 <b>Выберите день:</b>",
            parse_mode="HTML",
            reply_markup=build_admin_calendar(all_dates, today.year, today.month)
        )


@router.callback_query(AdminStates.choosing_day_del_slot, F.data.startswith("adm_day:"))
async def adm_del_slot_day(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day_date = callback.data.split(":")[1]
    slots = get_all_slots(day_date)

    if not slots:
        await callback.answer("На этот день нет слотов.", show_alert=True)
        return

    await state.clear()
    try:
        await callback.message.edit_text(
            f"📅 <b>{format_date_ru(day_date)}</b>\n\n"
            f"🗑 Выберите слот для удаления:\n"
            f"🟢 — свободный  🔴 — занятый (нельзя удалить)",
            parse_mode="HTML",
            reply_markup=admin_slots_delete_kb(slots, day_date)
        )
    except Exception:
        await callback.message.answer(
            f"Выберите слот:",
            reply_markup=admin_slots_delete_kb(slots, day_date)
        )


@router.callback_query(F.data.startswith("adm_del_slot_confirm:"))
async def adm_del_slot_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    _, day_date, slot_time = callback.data.split(":")

    # Проверяем есть ли запись на этот слот
    from database import get_bookings_for_day
    bookings = get_bookings_for_day(day_date)
    booking = next((b for b in bookings if b["slot_time"] == slot_time), None)

    if booking:
        # Слот занят - запрашиваем подтверждение
        text = (
            f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
            f"На слоте <b>{slot_time}</b> ({format_date_ru(day_date)}) есть запись:\n\n"
            f"👤 {booking['client_name']}\n"
            f"📞 {booking['phone']}\n"
            f"🆔 TG: {booking['user_id']}\n\n"
            f"Вы действительно хотите удалить этот слот?\n"
            f"Запись будет отменена!"
        )
        try:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=yes_no_kb(f"adm_del_slot_force:{day_date}:{slot_time}")
            )
        except Exception:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=yes_no_kb(f"adm_del_slot_force:{day_date}:{slot_time}")
            )
    else:
        # Слот свободен - удаляем сразу
        success = delete_time_slot(day_date, slot_time)
        if success:
            await callback.message.edit_text(
                f"✅ Слот <b>{slot_time}</b> на {format_date_ru(day_date)} удалён.",
                parse_mode="HTML",
                reply_markup=admin_menu_kb()
            )
        else:
            await callback.answer(
                "❌ Невозможно удалить: слот не существует.",
                show_alert=True
            )


@router.callback_query(F.data.startswith("adm_del_slot_force:"))
async def adm_del_slot_force(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()
    _, day_date, slot_time = callback.data.split(":")

    # Отменяем запись если есть
    from database import get_bookings_for_day, cancel_booking_by_id
    bookings = get_bookings_for_day(day_date)
    booking = next((b for b in bookings if b["slot_time"] == slot_time), None)

    if booking:
        cancel_booking_by_id(booking["id"], reason="Слот удален администратором")
        cancel_reminder(booking["id"])

        # Уведомляем клиента
        try:
            await bot.send_message(
                chat_id=booking["user_id"],
                text=(
                    f"😔 <b>Ваша запись была отменена мастером.</b>\n\n"
                    f"📅 {format_date_ru(day_date)} в {slot_time}\n\n"
                    f"Пожалуйста, запишитесь на другое время. 💅"
                ),
                parse_mode="HTML",
                reply_markup=__import__("keyboards").main_menu_kb()
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить клиента {booking['user_id']}: {e}")

    # Удаляем слот
    success = delete_time_slot(day_date, slot_time)

    try:
        await callback.message.edit_text(
            f"✅ Слот <b>{slot_time}</b> на {format_date_ru(day_date)} удалён (запись отменена).",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            f"✅ Слот {slot_time} удалён.",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Отменить запись клиента
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_cancel_booking")
async def adm_cancel_booking_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()

    from database.db import get_all_future_bookings
    bookings = get_all_future_bookings()

    if not bookings:
        try:
            await callback.message.edit_text(
                "📭 <b>Нет активных записей клиентов.</b>",
                parse_mode="HTML",
                reply_markup=admin_menu_kb()
            )
        except Exception:
            await callback.message.answer(
                "📭 Нет активных записей.",
                reply_markup=admin_menu_kb()
            )
        return

    await state.set_state(AdminStates.cancel_booking_input)

    try:
        await callback.message.edit_text(
            "❌ <b>Выберите запись для отмены:</b>",
            parse_mode="HTML",
            reply_markup=admin_bookings_kb(bookings)
        )
    except Exception:
        await callback.message.answer(
            "❌ <b>Выберите запись:</b>",
            parse_mode="HTML",
            reply_markup=admin_bookings_kb(bookings)
        )


@router.callback_query(AdminStates.cancel_booking_input, F.data.startswith("adm_cancel_confirm:"))
async def adm_cancel_booking_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()

    booking_id = int(callback.data.split(":")[1])
    cancelled = cancel_booking_by_id(booking_id)

    if cancelled is None:
        await callback.message.edit_text(
            "⚠️ Запись не найдена (возможно, уже отменена).",
            reply_markup=admin_menu_kb()
        )
        await state.clear()
        return

    # Удаляем напоминание
    cancel_reminder(booking_id)
    await state.clear()

    # Уведомляем клиента
    try:
        await bot.send_message(
            chat_id=cancelled["user_id"],
            text=(
                f"😔 <b>Ваша запись была отменена мастером.</b>\n\n"
                f"📅 {format_date_ru(cancelled['day_date'])} в {cancelled['slot_time']}\n\n"
                f"Пожалуйста, запишитесь на другое время. 💅"
            ),
            parse_mode="HTML",
            reply_markup=__import__("keyboards").main_menu_kb()
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {cancelled['user_id']}: {e}")

    try:
        await callback.message.edit_text(
            f"✅ <b>Запись #{booking_id} отменена.</b>\n\n"
            f"👤 {cancelled['client_name']}\n"
            f"📅 {format_date_ru(cancelled['day_date'])} в {cancelled['slot_time']}",
            parse_mode="HTML",
            reply_markup=admin_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            f"✅ Запись #{booking_id} отменена.",
            reply_markup=admin_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# История всех записей
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_show_history")
async def adm_show_history(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.answer()

    from database import get_all_clients
    clients = get_all_clients()

    if not clients:
        text = "📭 <b>Нет записей в базе данных.</b>"
    else:
        text = "📊 <b>История всех записей</b>\n\n"
        for client in clients[:20]:  # Показываем первые 20 записей
            status = "❌ Отменена" if client["is_cancelled"] else "✅ Активна"
            text += (
                f"🆔 <code>#{client['id']}</code> | {status}\n"
                f"👤 {client['client_name']} (@{client['username'] or 'нет'})\n"
                f"📞 {client['phone']}\n"
                f"📅 {format_date_ru(client['day_date'])} в {client['slot_time']}\n"
                f"🆔 TG: {client['user_id']}\n"
                f"🕐 Создано: {client['created_at']}\n"
                f"{'─' * 30}\n"
            )
        if len(clients) > 20:
            text += f"\n... и еще {len(clients) - 20} записей"

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_main_kb())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back_to_main_kb())
