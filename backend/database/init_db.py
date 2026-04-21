"""
Run this script once to initialize the database schema.

Usage:
    cd backend
    python -m database.init_db
"""

import os
from dotenv import load_dotenv

load_dotenv()

from database.db import init_db  # noqa: E402

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")
