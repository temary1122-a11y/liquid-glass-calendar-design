"""
Centralized configuration — single source of truth.

Every module imports from here instead of reading os.getenv directly,
so BOT_TOKEN / ADMIN_ID / ADMIN_SECRET_KEY are never duplicated.
"""

import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Helper: strip invisible characters from Render copy-paste
# ---------------------------------------------------------------------------

def _clean_env(val: str | None) -> str:
    """Remove zero-width, non-printable, and control characters."""
    if not val:
        return ""
    # Strip all whitespace including non-breaking spaces
    val = val.strip()
    # Keep only printable ASCII range (space through ~)
    val = re.sub(r'[^\x20-\x7E]', '', val)
    return val

# ---------------------------------------------------------------------------
# Required
# ---------------------------------------------------------------------------

BOT_TOKEN: str = _clean_env(os.getenv("BOT_TOKEN"))
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required in environment variables")

ADMIN_ID_INT: int = int(_clean_env(os.getenv("ADMIN_ID", "0")))
if not ADMIN_ID_INT:
    raise ValueError("ADMIN_ID is required in environment variables")

ADMIN_ID: str = str(ADMIN_ID_INT)

# ---------------------------------------------------------------------------
# Recommended (warn but don't crash)
# ---------------------------------------------------------------------------

ADMIN_SECRET_KEY: str = _clean_env(os.getenv("ADMIN_SECRET_KEY", ""))
if not ADMIN_SECRET_KEY:
    logging.warning("ADMIN_SECRET_KEY is not set — admin HMAC auth will fail")

DATABASE_URL: str = _clean_env(os.getenv("DATABASE_URL"))
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is required in environment variables")
# Log masked URL for debugging connection issues
_masked = DATABASE_URL.replace(DATABASE_URL.split('@')[0].split(':')[-1] if '@' in DATABASE_URL and ':' in DATABASE_URL.split('@')[0] else '***', '***')
logging.getLogger(__name__).info("DATABASE_URL: %s", _masked)

# ---------------------------------------------------------------------------
# Optional (with sensible defaults for dev)
# ---------------------------------------------------------------------------

WEBHOOK_URL: str = _clean_env(os.getenv(
    "WEBHOOK_URL",
    "https://liquid-glass-calendar-design.onrender.com/webhook",
))

MINI_APP_URL: str = _clean_env(os.getenv(
    "MINI_APP_URL",
    "https://temary1122-a11y.github.io/liquid-glass-calendar-design/",
))

ADDRESS: str = _clean_env(os.getenv("ADDRESS", "Тихий переулок, 4"))

PORT: int = int(_clean_env(os.getenv("PORT", "8000")))

ENCRYPTION_KEY: str = _clean_env(os.getenv("ENCRYPTION_KEY", ""))

GROQ_API_KEY: str = _clean_env(os.getenv("GROQ_API_KEY", ""))
