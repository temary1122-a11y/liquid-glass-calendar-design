"""
Health check endpoint — tests database connectivity.
"""

from fastapi import APIRouter
from sqlalchemy import text
from database.db import engine

router = APIRouter(tags=["health"])


@router.get("/health/db")
async def health_db():
    """Check database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)[:200]}
