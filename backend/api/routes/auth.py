"""
Auth route — checks if user is admin dynamically (no hardcoded ADMIN_ID in frontend).
"""

from fastapi import APIRouter, Header, HTTPException
from config import ADMIN_ID_INT

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/check-admin")
async def check_admin(
    x_init_data: str | None = Header(None, alias="x-init-data"),
):
    """
    Returns {is_admin: true/false} for the current Telegram user.
    Frontend sends Telegram initData in x-init-data header.
    Backend hashes it with ADMIN_SECRET_KEY to verify authenticity.
    """
    if not x_init_data:
        return {"is_admin": False}

    # Parse initData for user ID
    import urllib.parse
    params = urllib.parse.parse_qs(x_init_data)
    user_str = params.get("user", [None])[0]
    if not user_str:
        return {"is_admin": False}

    try:
        import json
        user = json.loads(user_str)
        user_id = int(user.get("id", 0))
    except (json.JSONDecodeError, (ValueError, TypeError)):
        return {"is_admin": False}

    return {"is_admin": user_id == ADMIN_ID_INT}
