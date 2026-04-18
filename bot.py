#!/usr/bin/env python3
# ============================================================
# bot.py — Точка входа: инициализация и запуск бота
# ============================================================

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from config import BOT_TOKEN
from database import init_db, get_all_future_bookings
from handlers import common, booking, admin
from utils.scheduler import scheduler, restore_reminders_from_db

# ── Настройка логирования ────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Действия при старте бота."""
    logger.info("Бот запускается...")

    # 1. Устанавливаем команды меню
    await set_bot_commands(bot)

    # 2. Инициализируем базу данных
    init_db()
    logger.info("База данных готова.")

    # 3. Запускаем планировщик
    scheduler.start()
    logger.info("APScheduler запущен.")

    # 4. Восстанавливаем напоминания из БД
    future_bookings = get_all_future_bookings()
    restore_reminders_from_db(bot, future_bookings)

    # 5. Уведомляем администратора о запуске
    from config import ADMIN_ID
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text="✅ <b>Бот запущен и готов к работе!</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить администратора: {e}")


async def set_bot_commands(bot: Bot) -> None:
    """Устанавливает команды меню бота."""
    commands = [
        BotCommand(command="start", description="🚀 Главное меню"),
        BotCommand(command="cancel", description="❌ Отменить запись"),
        BotCommand(command="mybooking", description="📋 Моя запись"),
        BotCommand(command="prices", description="💰 Прайсы"),
        BotCommand(command="admin", description="⚙️ Админ-панель"),
        BotCommand(command="backup", description="📦 Бэкап БД (админ)"),
    ]

    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Команды меню установлены")
    except Exception as e:
        logger.warning(f"Не удалось установить команды меню: {e}")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота."""
    logger.info("Бот останавливается...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Планировщик остановлен.")


async def main() -> None:
    # Логируем токен для диагностики (скрываем середину)
    if BOT_TOKEN:
        token_preview = BOT_TOKEN[:10] + "..." + BOT_TOKEN[-10:] if len(BOT_TOKEN) > 20 else BOT_TOKEN
        logger.info(f"BOT_TOKEN loaded: {token_preview}")
    else:
        logger.error("BOT_TOKEN is empty or None!")

    # ── Создаём экземпляр бота ──────────────────────────────
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # ── Диспетчер с FSM-хранилищем в памяти ─────────────────
    dp = Dispatcher(storage=MemoryStorage())

    # ── Регистрируем роутеры ─────────────────────────────────
    # Порядок важен: более специфичные — первыми
    dp.include_router(admin.router)
    dp.include_router(booking.router)
    dp.include_router(common.router)

    # ── События старта/остановки ─────────────────────────────
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Запускаем polling ────────────────────────────────────
    logger.info("Начинаем polling...")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
