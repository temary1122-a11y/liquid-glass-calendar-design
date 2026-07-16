"""
aiogram 3.x bot setup.

Exports:
  bot  — Bot instance
  dp   — Dispatcher instance

Used by main.py to:
  1. Register webhook on startup
  2. Feed updates from POST /webhook

Router order matters in aiogram 3: first match wins.
- common_router FIRST: handles button text, /start, /cancel, callbacks
- admin_voice LAST: catch-all for admin voice/bulk/text commands
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.handlers.common import router as common_router
from bot.handlers.admin_voice import router as admin_voice_router
from bot.handlers.admin_photo import router as admin_photo_router
from config import BOT_TOKEN

# ---------------------------------------------------------------------------
# Instantiate bot and dispatcher (singleton)
# ---------------------------------------------------------------------------

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())

# Register routers -- ORDER MATTERS (first match wins)
dp.include_router(common_router)       # /start, /cancel, /help, button text, callbacks
dp.include_router(admin_photo_router)  # /setbg, photo, document (admin background change)
dp.include_router(admin_voice_router)  # /vc, /bulk, voice, bulk auto-detect, admin text cmd


# ---------------------------------------------------------------------------
# Set bot commands (menu)
# ---------------------------------------------------------------------------


async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="📅 Записаться"),
        BotCommand(command="mybooking", description="📋 Моя запись"),
        BotCommand(command="cancel", description="❌ Отменить запись"),
        BotCommand(command="vc", description="🎤 Голосовые команды (админ)"),
        BotCommand(command="bulk", description="📋 Массовое добавление слотов (админ)"),
        BotCommand(command="setbg", description="🖼 Сменить фон Mini App (админ)"),
        BotCommand(command="resetbg", description="🔄 Сбросить фон на дефолтный (админ)"),
        BotCommand(command="help", description="❓ Помощь"),
    ]

    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
