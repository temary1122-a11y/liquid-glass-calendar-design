#!/usr/bin/env python3
"""
Генератор случайного секретного ключа для HMAC аутентификации.
"""

import secrets
import base64

# Генерируем 32 байта случайных данных (256 бит)
secret_key = secrets.token_bytes(32)

# Кодируем в base64 для удобства использования в .env
secret_key_b64 = base64.b64encode(secret_key).decode('utf-8')

print("Сгенерирован секретный ключ для ADMIN_SECRET_KEY:")
print(secret_key_b64)
print("\nСкопируйте этот ключ в ваш .env файл:")
print(f"ADMIN_SECRET_KEY={secret_key_b64}")
