"""
Добавляет колонку reminder_sent в существующую таблицу bookings.
Безопасно — использует IF NOT EXISTS, не падает если колонка уже есть.
"""

import os
import sys

# Добавляем backend/ в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import engine
from sqlalchemy import text


def migrate():
    """Запустить миграцию."""
    with engine.connect() as conn:
        # 1. Добавляем колонку reminder_sent (для напоминаний)
        conn.execute(text("""
            ALTER TABLE bookings 
            ADD COLUMN IF NOT EXISTS reminder_sent INTEGER DEFAULT 0
        """))
        conn.commit()
        print("✅ reminder_sent column added (or already exists)")

        # 2. Добавляем колонку service_id если нет
        conn.execute(text("""
            ALTER TABLE bookings 
            ADD COLUMN IF NOT EXISTS service_id VARCHAR(50)
        """))
        conn.commit()
        print("✅ service_id column added (or already exists)")


if __name__ == "__main__":
    migrate()
