# ============================================================
# utils/message_helpers.py — Helper функции для отправки сообщений
# ============================================================

import logging
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from typing import Optional

logger = logging.getLogger(__name__)


async def safe_edit_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> bool:
    """
    Безопасно редактирует сообщение callback.
    При ошибке отправляет новое сообщение.
    Возвращает True если успешно.
    """
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        logger.warning(f"Ошибка редактирования сообщения: {e}, отправляю новое")
        try:
            await callback.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as e2:
            logger.error(f"Ошибка отправки сообщения: {e2}")
            return False


async def safe_answer(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> bool:
    """
    Безопасно отправляет ответ на сообщение.
    Возвращает True если успешно.
    """
    try:
        await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False


async def check_and_notify_active_booking(
    callback: CallbackQuery,
    user_id: int,
    format_date_func,
    back_keyboard_func,
) -> bool:
    """
    Проверяет наличие активной записи и уведомляет пользователя.
    Возвращает True если активная запись существует.
    """
    from database import get_user_booking
    
    booking = get_user_booking(user_id)
    if booking:
        text = (
            f"⚠️ <b>У вас уже есть активная запись!</b>\n\n"
            f"📅 <b>Дата:</b> {format_date_func(booking['day_date'])}\n"
            f"🕐 <b>Время:</b> {booking['slot_time']}\n\n"
            f"Сначала отмените текущую запись, чтобы создать новую."
        )
        await safe_edit_text(
            callback,
            text,
            reply_markup=back_keyboard_func(),
            parse_mode="HTML"
        )
        return True
    return False
