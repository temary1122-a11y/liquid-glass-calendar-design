"""
aiogram 3.x bot setup.

Exports:
  bot  вЂ” Bot instance
  dp   вЂ” Dispatcher instance

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

from bot.handlers.ai_chat import router as ai_chat_router
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
dp.include_router(ai_chat_router)
dp.include_router(common_router)


# ---------------------------------------------------------------------------
# Set bot commands (menu)
# ---------------------------------------------------------------------------


async def set_bot_commands():
    """РЈСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ РєРѕРјР°РЅРґС‹ Р±РѕС‚Р° РґР»СЏ РјРµРЅСЋ."""
    commands = [
        BotCommand(command="start", description="рџ“… Р—Р°РїРёСЃР°С‚СЊСЃСЏ"),
        BotCommand(command="mybooking", description="рџ“‹ РњРѕСЏ Р·Р°РїРёСЃСЊ"),
        BotCommand(command="cancel", description="вќЊ РћС‚РјРµРЅРёС‚СЊ Р·Р°РїРёСЃСЊ"),
        BotCommand(command="help", description="вќ“ РџРѕРјРѕС‰СЊ"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

