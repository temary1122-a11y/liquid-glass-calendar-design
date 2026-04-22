"""
FastAPI application entry point.

Startup sequence:
  1. Load .env
  2. Initialize database (create tables)
  3. Set up aiogram bot webhook
  4. Start APScheduler for reminders
  5. Register all API routers
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from database.db import init_db
from api.routes import booking, profile, admin
from api.websocket import router as ws_router
from bot.bot import bot, dp
from bot.handlers.webhook import router as webhook_router, set_bot_and_dispatcher
from bot.scheduler import start_scheduler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Lashes Booking API",
    description="Backend for Telegram Mini App — lash master booking",
    version="1.0.0",
)

# Attach limiter
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again in a minute."},
    )


# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(booking.router)
app.include_router(profile.router)
app.include_router(admin.router)
app.include_router(ws_router)
app.include_router(webhook_router)

# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

WEBHOOK_URL: str = os.getenv(
    "WEBHOOK_URL",
    "https://liquid-glass-calendar-design.onrender.com/webhook",
)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("=== Starting Lashes Booking Backend ===")

    # 1. Init database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")

    # 2. Inject bot/dp into webhook handler
    set_bot_and_dispatcher(bot, dp)

    # 3. Set Telegram webhook
    try:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info("Telegram webhook set: %s", WEBHOOK_URL)
    except Exception as exc:
        logger.error("Failed to set webhook: %s", exc)

    # 4. Start reminder scheduler
    start_scheduler()
    logger.info("APScheduler started.")

    logger.info("=== Backend is ready ===")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Shutting down...")
    try:
        # Don't delete webhook - it should persist across restarts
        await bot.session.close()
    except Exception:
        pass
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/", tags=["health"])
async def root() -> dict:
    return {
        "status": "ok",
        "service": "Lashes Booking API",
        "version": "1.0.0",
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
