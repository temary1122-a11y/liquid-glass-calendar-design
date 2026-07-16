"""
Settings endpoint — dynamic configuration for the frontend.
Currently provides: custom background image URL.
"""

import json
import logging
import os

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])

# Resolve static/ directory relative to backend/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(_BACKEND_DIR, "static")
META_FILE = "background_meta.json"
BG_FILE = "background.jpg"


@router.get("/settings")
async def get_settings():
    """Return dynamic settings: custom background presence + cache-bust timestamp."""
    bg_meta_path = os.path.join(STATIC_DIR, META_FILE)
    bg_path = os.path.join(STATIC_DIR, BG_FILE)

    custom_background = False
    bg_updated_at = None
    bg_info = None

    if os.path.exists(bg_path) and os.path.exists(bg_meta_path):
        try:
            with open(bg_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            custom_background = True
            bg_updated_at = meta.get("updated_at")
            bg_info = {
                "width": meta.get("width"),
                "height": meta.get("height"),
                "file_size_kb": meta.get("file_size_kb"),
            }
        except Exception as exc:
            logger.warning("Failed to read background meta: %s", exc)

    return {
        "custom_background": custom_background,
        "bg_updated_at": bg_updated_at,
        "bg_info": bg_info,
    }
