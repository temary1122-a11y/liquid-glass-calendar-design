"""
Webhook handler — registered in main.py as a FastAPI route.
Telegram POSTs updates to /webhook.
"""

import json
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])

# Bot and dispatcher are initialised in bot/bot.py and imported here.
# They are set by main.py after startup.
_bot: Bot | None = None
_dp: Dispatcher | None = None


def set_bot_and_dispatcher(bot: Bot, dp: Dispatcher) -> None:
    """Called from main.py startup to inject bot/dp references."""
    global _bot, _dp
    _bot = bot
    _dp = dp


@router.post("/webhook")
async def webhook_endpoint(request: Request) -> Response:
    """
    Receives Telegram updates via POST /webhook.
    Feeds the update to aiogram Dispatcher.
    """
    if _bot is None or _dp is None:
        logger.error("Bot/Dispatcher not initialised")
        return Response(status_code=503)

    try:
        body = await request.body()
        update_data = json.loads(body)
        update = Update.model_validate(update_data)
        await _dp.feed_update(_bot, update)
    except Exception as exc:
        logger.exception("Error processing webhook update: %s", exc)

    # Always return 200 to Telegram
    return Response(status_code=200)
