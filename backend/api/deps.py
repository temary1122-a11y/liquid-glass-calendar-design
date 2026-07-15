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

    NOTE: Если BOT_TOKEN не задан — пропускаем проверку (dev mode).
    """
    if not init_data or not BOT_TOKEN:
        # Dev mode: accept without validation
        if not BOT_TOKEN:
            return True
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
                uid = int(user_obj.get("id", 0))
                if uid:
                    return uid
            except (json.JSONDecodeError, ValueError):
                pass
    # Also try from plain user_id param (for debugging / simple auth)
    for pair in init_data.split("&"):
        if pair.startswith("user_id="):
            try:
                return int(pair.split("=", 1)[1])
            except ValueError:
                pass
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

    NOTE: Если BOT_TOKEN не задан — пропускаем валидацию (dev mode),
    но всё равно извлекаем user_id из initData.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="No initData provided")

    # Dev mode: extract user_id without HMAC verification
    if not BOT_TOKEN:
        uid = extract_user_id_from_init_data(x_init_data)
        if uid:
            return uid
        raise HTTPException(status_code=401, detail="No user_id in initData")

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

    NOTE: Также принимает x-user-id header для простой авторизации (dev mode).
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="No initData provided (Admin rights required)")

    # Dev mode: if BOT_TOKEN is empty, accept any admin request (for local testing)
    if not BOT_TOKEN:
        # Extract user_id from initData without verifying HMAC
        uid = extract_user_id_from_init_data(x_init_data)
        if uid and str(uid) == str(ADMIN_ID):
            return True
        raise HTTPException(status_code=403, detail="Forbidden: You are not the administrator")

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
    Возвращает user_id или None (анонимный доступ).
    Если BOT_TOKEN не задан — извлекаем user_id без проверки подписи (dev mode).
    """
    if not init_data:
        return None

    # Dev mode: skip HMAC, just extract user_id
    if not BOT_TOKEN:
        return extract_user_id_from_init_data(init_data)

    if not verify_init_data(init_data):
        return None

    if not check_auth_date(init_data):
        return None

    return extract_user_id_from_init_data(init_data)
