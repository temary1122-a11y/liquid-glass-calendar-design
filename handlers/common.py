# ============================================================
# handlers/common.py — Общие обработчики (старт, меню, прайс, портфолио)
# ============================================================

import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, PRICES_POST_LINK
from keyboards import main_menu_kb, admin_menu_kb, back_to_main_kb

logger = logging.getLogger(__name__)
router = Router()


# ────────────────────────────────────────────────────────────
# /start
# ────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Приветственное сообщение и главное меню."""
    await state.clear()

    welcome_text = (
        f"👋 <b>Добро пожаловать!</b>\n\n"
        f"💅 Я помогу вам записаться на наращивание ресниц.\n\n"
        f"✨ Выберите нужный раздел:"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu_kb())


# ────────────────────────────────────────────────────────────
# /admin — панель администратора
# ────────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этому разделу.")
        return
    await state.clear()
    await message.answer(
        "🔧 <b>Панель администратора</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )


# ────────────────────────────────────────────────────────────
# /cancel — отменить запись
# ────────────────────────────────────────────────────────────
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Быстрая команда для отмены записи."""
    from handlers.booking import cancel_booking
    await cancel_booking(message, state)


# ────────────────────────────────────────────────────────────
# /mybooking — моя запись
# ────────────────────────────────────────────────────────────
@router.message(Command("mybooking"))
async def cmd_mybooking(message: Message):
    """Быстрая команда для просмотра своей записи."""
    from database import get_user_booking
    from utils import format_date_ru
    
    booking = get_user_booking(message.from_user.id)
    if not booking:
        text = "📭 <b>У вас нет активных записей.</b>\n\nЗапишитесь через кнопку «📅 Записаться»."
    else:
        text = (
            f"📋 <b>Ваша запись</b>\n\n"
            f"🆔 <code>#{booking['id']}</code>\n"
            f"📅 <b>Дата:</b> {format_date_ru(booking['day_date'])}\n"
            f"🕐 <b>Время:</b> {booking['slot_time']}\n"
            f"👤 <b>Имя:</b> {booking['client_name']}\n"
            f"📞 <b>Телефон:</b> {booking['phone']}\n\n"
            f"Для отмены нажмите «❌ Отменить запись»."
        )
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_main_kb())


# ────────────────────────────────────────────────────────────
# /prices — прайсы
# ────────────────────────────────────────────────────────────
@router.message(Command("prices"))
async def cmd_prices(message: Message):
    """Быстрая команда для просмотра прайсов."""
    await message.answer(
        "💰 <b>Прайс-лист</b>\n\nПосмотрите прайсы по ссылке ниже 👇",
        parse_mode="HTML",
        reply_markup=back_to_main_kb()
    )
    await message.answer(PRICES_POST_LINK)


# /backup — скачать БД (только для админа)
# ────────────────────────────────────────────────────────────
@router.message(Command("backup"))
async def cmd_backup(message: Message):
    """Скачать БД файл (только для админа)."""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    from config import DB_PATH
    import os

    if not os.path.exists(DB_PATH):
        await message.answer("❌ Файл БД не найден.")
        return

    try:
        await message.answer_document(
            document=open(DB_PATH, "rb"),
            caption=f"📦 Бэкап БД от {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке БД: {e}")


# ────────────────────────────────────────────────────────────
# Callback: назад в главное меню
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(
            "📋 <b>Главное меню</b>\n\nВыберите нужный раздел:",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            "📋 <b>Главное меню</b>\n\nВыберите нужный раздел:",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )


# ────────────────────────────────────────────────────────────
# Прайсы (без FSM)
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "show_prices")
async def show_prices(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text(
            "💰 <b>Прайс-лист</b>\n\nПосмотрите прайсы по ссылке ниже 👇",
            parse_mode="HTML",
            reply_markup=back_to_main_kb()
        )
        await callback.message.answer(PRICES_POST_LINK)
    except Exception:
        await callback.message.answer(
            "💰 <b>Прайс-лист</b>\n\nПосмотрите прайсы по ссылке ниже 👇",
            parse_mode="HTML",
            reply_markup=back_to_main_kb()
        )
        await callback.message.answer(PRICES_POST_LINK)


# ────────────────────────────────────────────────────────────
# Игнорируем «пустые» callback от календаря
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "cal_ignore")
async def cal_ignore(callback: CallbackQuery):
    await callback.answer()


# ────────────────────────────────────────────────────────────
# Моя запись
# ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "my_booking")
async def my_booking(callback: CallbackQuery):
    from database import get_user_booking
    from utils import format_date_ru
    await callback.answer()
    booking = get_user_booking(callback.from_user.id)
    if not booking:
        text = "📭 <b>У вас нет активных записей.</b>\n\nЗапишитесь через кнопку «📅 Записаться»."
    else:
        text = (
            f"📋 <b>Ваша запись</b>\n\n"
            f"🆔 <code>#{booking['id']}</code>\n"
            f"📅 <b>Дата:</b> {format_date_ru(booking['day_date'])}\n"
            f"🕐 <b>Время:</b> {booking['slot_time']}\n"
            f"👤 <b>Имя:</b> {booking['client_name']}\n"
            f"📞 <b>Телефон:</b> {booking['phone']}\n\n"
            f"Для отмены нажмите «❌ Отменить запись»."
        )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_main_kb())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back_to_main_kb())
