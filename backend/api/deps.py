"""
FastAPI dependency functions for authentication:
  - initData hash verification (Telegram WebApp)
  - Admin HMAC signature verification
  - Auth date expiry check
  - WebSocket auth via initData
"""

import hmac
import hashlib
import json
from datetime import datetime, timedelta
from urllib.parse import parse_qs, unquote

from fastapi import Header, HTTPException, Query, WebSocket, WebSocketDisconnect

from config import ADMIN_ID, ADMIN_SECRET_KEY, BOT_TOKEN


# ---------------------------------------------------------------------------
# Telegram initData verification (HMAC-SHA256, standard Telegram algorithm)
# ---------------------------------------------------------------------------

def verify_init_data(init_data: str) -> bool:
    """
    Проверяет HMAC-SHA256 подпись Telegram initData.
    Возвращает True если подпись валидна.

    Алгоритм:
    1. Извлечь hash= из строки
    2. Отсортировать остальные пары key=value
    3. Соединить через \n
    4. HMAC-SHA256(HMAC-SHA256("WebAppData", bot_token), data_check_string)
    5. Сравнить с hash
    """
    if not init_data:
        return False

    hash_value: str | None = None
    pairs: list[str] = []

    for pair in init_data.split("&"):
        if pair.startswith("hash="):
            hash_value = pair.split("=", 1)[1]
        else:
            pairs.append(pair)

    if not hash_value:
        return False

    pairs.sort()
    data_check_string = "\n".join(pairs)

    try:
        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        hash_check = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
    except Exception:
        return False

    return hmac.compare_digest(hash_check, hash_value)


def check_auth_date(init_data: str) -> bool:
    """
    Проверяет что auth_date не старше 24 часов.
    """
    for pair in init_data.split("&"):
        if pair.startswith("auth_date="):
            try:
                auth_date = int(pair.split("=", 1)[1])
                auth_datetime = datetime.fromtimestamp(auth_date)
                return datetime.now() - auth_datetime < timedelta(hours=24)
            except (ValueError, OSError):
                return False
    return False


def extract_user_id_from_init_data(init_data: str) -> int | None:
    """
    Извлекает user.id из поля user= в initData.
    """
    for pair in init_data.split("&"):
        if pair.startswith("user="):
            raw = pair.split("=", 1)[1]
            raw = unquote(raw)
            try:
                user_obj = json.loads(raw)
                return int(user_obj.get("id", 0)) or None
            except (json.JSONDecodeError, ValueError):
                return None
    return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user_id(
    x_init_data: str = Header(None, alias="x-init-data"),
) -> int:
    """
    Dependency: проверяет initData и возвращает user_id.
    Поднимает 401 если данные невалидны или просрочены.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="No initData provided")

    if not verify_init_data(x_init_data):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    if not check_auth_date(x_init_data):
        raise HTTPException(status_code=401, detail="initData expired")

    user_id = extract_user_id_from_init_data(x_init_data)
    if not user_id:
        raise HTTPException(status_code=401, detail="No user_id in initData")

    return user_id


async def verify_admin(
    x_init_data: str = Header(None, alias="x-init-data"),
) -> bool:
    """
    Dependency: проверяет авторизацию администратора через Telegram initData.
    Поднимает 401/403 если данные невалидны.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="No initData provided (Admin rights required)")

    if not verify_init_data(x_init_data):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    if not check_auth_date(x_init_data):
        raise HTTPException(status_code=401, detail="initData expired")

    user_id = extract_user_id_from_init_data(x_init_data)
    if not user_id:
        raise HTTPException(status_code=401, detail="No user_id in initData")

    if str(user_id) != str(ADMIN_ID):
        raise HTTPException(status_code=403, detail="Forbidden: You are not the administrator")

    return True


# ---------------------------------------------------------------------------
# WebSocket auth helper
# ---------------------------------------------------------------------------

async def verify_ws_init_data(
    init_data: str = Query(None),
) -> int | None:
    """
    Проверяет initData переданный как query-параметр при WebSocket подключении.
    Возвращает user_id или поднимает ошибку.
    Используется в WebSocket endpoint для аутентификации.
    """
    if not init_data:
        return None  # allow anonymous (non-admin) connections for now

    if not verify_init_data(init_data):
        return None  # invalid signature → treat as anonymous

    if not check_auth_date(init_data):
        return None  # expired → treat as anonymous

    return extract_user_id_from_init_data(init_data)
