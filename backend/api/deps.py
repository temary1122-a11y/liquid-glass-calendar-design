"""
FastAPI dependency functions for authentication:
  - initData hash verification (Telegram WebApp)
  - Admin HMAC signature verification
  - Auth date expiry check
"""

import hmac
import hashlib
import json
import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs, unquote

from fastapi import Header, HTTPException

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: str = os.getenv("ADMIN_ID", "")
ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "f9XnzG1Ib0jYz4iZ8PoU518CcF43M1yEz1liGgUDYpA")


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
    3. Соединить через \\n
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
# Admin HMAC signature verification
# Replicates the EXACT same logic as the TypeScript frontend createAdminSignature()
# ---------------------------------------------------------------------------

def _admin_hash(admin_id: str, secret_key: str) -> str:
    """
    Упрощённая (не криптографическая) HMAC подпись — точная копия frontend.

    TypeScript reference:
        function createAdminSignature(adminId: string): string {
          const secretBytes = new TextEncoder().encode(ADMIN_SECRET_KEY);
          const messageBytes = new TextEncoder().encode(adminId);
          let hash = 0;
          const combined = new Uint8Array([...secretBytes, ...messageBytes]);
          for (let i = 0; i < combined.length; i++) {
            hash = ((hash << 5) - hash) + combined[i];
            hash = hash & hash;  // Convert to 32-bit integer
          }
          return Math.abs(hash).toString(16).padStart(64, '0').slice(0, 64);
        }

    Python replication uses signed 32-bit integer arithmetic to match JS behaviour.
    """
    secret_bytes = secret_key.encode("utf-8")
    message_bytes = admin_id.encode("utf-8")
    combined = secret_bytes + message_bytes

    hash_value: int = 0
    for byte in combined:
        # JS: hash = ((hash << 5) - hash) + byte
        hash_value = ((hash_value << 5) - hash_value) + byte
        # JS: hash = hash & hash  →  convert to signed 32-bit int
        hash_value = hash_value & 0xFFFFFFFF  # keep 32 bits
        if hash_value >= 0x80000000:          # sign-extend
            hash_value -= 0x100000000

    expected_hex = (
        abs(hash_value).to_bytes(4, "big").hex()  # 8 hex chars
        .zfill(64)[:64]                            # padStart(64,'0').slice(0,64)
    )
    return expected_hex


def verify_admin_signature(admin_id: str, signature: str) -> bool:
    """Проверяет HMAC подпись админа."""
    expected = _admin_hash(admin_id, ADMIN_SECRET_KEY)
    return signature == expected


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
    x_admin_id: str = Header(None, alias="x-admin-id"),
    x_admin_signature: str = Header(None, alias="x-admin-signature"),
) -> bool:
    """
    Dependency: проверяет авторизацию администратора.
    Поднимает 401/403 если данные невалидны.
    """
    if not x_admin_id or not x_admin_signature:
        raise HTTPException(status_code=401, detail="Admin credentials required")

    if x_admin_id != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Not admin")

    if not verify_admin_signature(x_admin_id, x_admin_signature):
        raise HTTPException(status_code=403, detail="Invalid admin signature")

    return True
