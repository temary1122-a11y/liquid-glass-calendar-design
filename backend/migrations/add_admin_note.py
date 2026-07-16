"""
Migration: add admin_note column to bookings table.

Usage: called from main.py on_startup (idempotent).
"""

import logging
from database.db import engine

logger = logging.getLogger(__name__)


def migrate():
    """Add admin_note column if it doesn't exist."""
    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.exec_driver_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='bookings' AND column_name='admin_note'"
            ).fetchone()

            if result:
                logger.info("migrations/add_admin_note: already applied")
                return

            conn.exec_driver_sql(
                "ALTER TABLE bookings ADD COLUMN admin_note TEXT"
            )
            conn.commit()
            logger.info("migrations/add_admin_note: applied successfully")
    except Exception as exc:
        logger.warning("migrations/add_admin_note: could not apply (may already exist): %s", exc)
