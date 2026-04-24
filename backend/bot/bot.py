"""
aiogram 3.x bot setup.

Exports:
  bot  — Bot instance
  dp   — Dispatcher instance

Used by main.py to:
  1. Register webhook on startup
  2. Feed updates from POST /webhook
"""

import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.handlers.common import router as common_router

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ---------------------------------------------------------------------------
# Instantiate bot and dispatcher (singleton)
# ---------------------------------------------------------------------------

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())

# Register routers
dp.include_router(common_router)


# ---------------------------------------------------------------------------
# Set bot commands (menu)
# ---------------------------------------------------------------------------


async def set_bot_commands():
    """Устанавливает команды бота для меню."""
    commands = [
        BotCommand(command="start", description="📅 Записаться"),
        BotCommand(command="mybooking", description="📋 Моя запись"),
        BotCommand(command="cancel", description="❌ Отменить запись"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
