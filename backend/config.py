"""
Centralized configuration — single source of truth.

Every module imports from here instead of reading os.getenv directly,
so BOT_TOKEN / ADMIN_ID / ADMIN_SECRET_KEY are never duplicated.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Required
# ---------------------------------------------------------------------------

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required in environment variables")

ADMIN_ID_INT: int = int(os.getenv("ADMIN_ID", "0"))
if not ADMIN_ID_INT:
    raise ValueError("ADMIN_ID is required in environment variables")

# String form for Telegram chat_id (also works with int, kept for convenience)
ADMIN_ID: str = str(ADMIN_ID_INT)

# ---------------------------------------------------------------------------
# Recommended (warn but don't crash)
# ---------------------------------------------------------------------------

ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "")
if not ADMIN_SECRET_KEY:
    logging.getLogger(__name__).warning(
        "ADMIN_SECRET_KEY is not set — admin HMAC auth will fail"
    )

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
# Strip invisible characters that sometimes sneak in from Render dashboard copy-paste
DATABASE_URL = DATABASE_URL.strip().replace("\n", "").replace("\r", "")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is required in environment variables")

# ---------------------------------------------------------------------------
# Optional (with sensible defaults for dev)
# ---------------------------------------------------------------------------

WEBHOOK_URL: str = os.getenv(
    "WEBHOOK_URL",
    "https://liquid-glass-calendar-design.onrender.com/webhook",
)

MINI_APP_URL: str = os.getenv(
    "MINI_APP_URL",
    "https://temary1122-a11y.github.io/liquid-glass-calendar-design/",
)

ADDRESS: str = os.getenv("ADDRESS", "Тихий переулок, 4")

PORT: int = int(os.getenv("PORT", "8000"))

# Encryption key for sensitive PII fields (phone numbers).
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Must be set in production or phone encryption will fail.
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# Groq API key for voice commands & NLP.
# Get free API key at https://console.groq.com/keys
# If not set, voice commands fall back to text-only mode.
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
