# ============================================================
# keyboards/inline.py — Все inline-клавиатуры бота
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import PORTFOLIO_LINK, MINI_APP_URL


# ────────────────────────────────────────────────────────────
# Главное меню
# ────────────────────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", web_app=WebAppInfo(url=MINI_APP_URL)))
    builder.row(InlineKeyboardButton(text="📋 Моя запись", callback_data="my_booking"))
    builder.row(InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking"))
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Портфолио
# ────────────────────────────────────────────────────────────
def portfolio_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🖼 Смотреть портфолио", url=PORTFOLIO_LINK)
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Временные слоты
# ────────────────────────────────────────────────────────────
def time_slots_kb(slots: list, day_date: str) -> InlineKeyboardMarkup:
    """Кнопки доступных временных слотов."""
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(
            text=f"🕐 {slot['slot_time']}",
            callback_data=f"slot:{day_date}:{slot['slot_time']}"
        )
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(text="🔙 Выбрать другой день", callback_data="book_start")
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Подтверждение записи
# ────────────────────────────────────────────────────────────
def confirm_booking_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking_process"),
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Отмена записи пользователем
# ────────────────────────────────────────────────────────────
def cancel_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data="do_cancel_booking"),
        InlineKeyboardButton(text="🔙 Нет, назад", callback_data="back_to_main"),
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Кнопка «Назад в меню»
# ────────────────────────────────────────────────────────────
def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Админ-панель — главное меню
# ────────────────────────────────────────────────────────────
def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✨ Mini App", web_app=WebAppInfo(url=f"{MINI_APP_URL}?admin=true")))
    builder.row(InlineKeyboardButton(text="📊 История записей", callback_data="adm_show_history"))
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="back_to_main"))
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Список слотов для удаления (админ)
# ────────────────────────────────────────────────────────────
def admin_slots_delete_kb(slots: list, day_date: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        status = "🔴" if slot["is_booked"] else "🟢"
        builder.button(
            text=f"{status} {slot['slot_time']}",
            callback_data=f"adm_del_slot_confirm:{day_date}:{slot['slot_time']}"
        )
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Список записей для отмены (админ)
# ────────────────────────────────────────────────────────────
def admin_bookings_kb(bookings: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bookings:
        builder.button(
            text=f"❌ {b['day_date']} {b['slot_time']} — {b['client_name']}",
            callback_data=f"adm_cancel_confirm:{b['id']}"
        )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    )
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
# Подтверждение действия (да/нет)
# ────────────────────────────────────────────────────────────
def yes_no_kb(yes_data: str, no_data: str = "admin_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
        InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
    )
    return builder.as_markup()
