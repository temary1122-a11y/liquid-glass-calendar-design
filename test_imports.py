#!/usr/bin/env python3
"""
Тестовый скрипт для проверки импортов без валидации .env.
Временно устанавливает mock переменные окружения.
"""

import os
import sys

# Устанавливаем тестовые переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_12345'
os.environ['ADMIN_ID'] = '123456789'
os.environ['ADMIN_SECRET_KEY'] = 'test_secret_key_abc123'
os.environ['DB_PATH'] = ':memory:'  # In-memory database

# Теперь импортируем модули
print("Testing imports...")
try:
    from config import ADMIN_ID, ADMIN_SECRET_KEY, BOT_TOKEN, DB_PATH
    print(f"✅ config.py imported: ADMIN_ID={ADMIN_ID}, SECRET_KEY={ADMIN_SECRET_KEY[:10]}...")
except Exception as e:
    print(f"❌ config.py import failed: {e}")
    sys.exit(1)

try:
    from database import db
    print("✅ database.db imported")
except Exception as e:
    print(f"❌ database.db import failed: {e}")
    sys.exit(1)

try:
    from utils.message_helpers import safe_edit_text, check_and_notify_active_booking
    print("✅ utils.message_helpers imported")
except Exception as e:
    print(f"❌ utils.message_helpers import failed: {e}")
    sys.exit(1)

try:
    from handlers import booking
    print("✅ handlers.booking imported")
except Exception as e:
    print(f"❌ handlers.booking import failed: {e}")
    sys.exit(1)

try:
    from api.routes import admin
    print("✅ api.routes.admin imported")
except Exception as e:
    print(f"❌ api.routes.admin import failed: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
