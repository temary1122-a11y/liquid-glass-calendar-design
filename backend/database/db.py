import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, UniqueConstraint, Index, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lashes.db")

# asyncpg requires postgresql+asyncpg:// scheme, but for sync SQLAlchemy use psycopg2
# Render provides DATABASE_URL with postgres:// — fix for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class WorkDay(Base):
    __tablename__ = "work_days"

    id = Column(Integer, primary_key=True, index=True)
    day_date = Column(String(10), unique=True, nullable=False)  # YYYY-MM-DD
    is_closed = Column(Integer, default=0)  # 0 = False, 1 = True (Supabase uses integer)


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    day_date = Column(String(10), nullable=False)  # YYYY-MM-DD (Supabase: text field)
    slot_time = Column(String(5), nullable=False)  # HH:MM (renamed from time)
    is_booked = Column(Integer, default=0)  # 0 = False, 1 = True (Supabase uses integer)

    # Relationship to WorkDay (via day_date)
    work_day = relationship(
        "WorkDay",
        primaryjoin="TimeSlot.day_date == WorkDay.day_date",
        foreign_keys=[day_date],
        backref="time_slots"
    )

    __table_args__ = (
        UniqueConstraint("day_date", "slot_time", name="unique_day_time"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    day_date = Column(String(10), nullable=False)  # YYYY-MM-DD (Supabase: direct field)
    slot_time = Column(String(5), nullable=False)  # HH:MM (Supabase: direct field)
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled, completed
    note = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)  # ISO format string (Supabase: text)
    is_cancelled = Column(Integer, default=0)  # 0 = False, 1 = True (Supabase field)
    cancel_reason = Column(Text, nullable=True)  # renamed from cancellation_reason
    cancelled_at = Column(String, nullable=True)  # ISO format string (Supabase: text)
    service_id = Column(String(50), nullable=True)  # NEW field (Supabase has it)

    # Relationship to TimeSlot (via day_date and slot_time)
    slot = relationship(
        "TimeSlot",
        primaryjoin="and_(Booking.day_date == TimeSlot.day_date, Booking.slot_time == TimeSlot.slot_time)",
        foreign_keys=[day_date, slot_time],
        backref="booking"
    )

    __table_args__ = (
        Index("idx_bookings_user_id", "user_id"),
        Index("idx_bookings_status", "status"),
    )


def get_db():
    """Dependency: yields a SQLAlchemy session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    print("[database] Initializing database...")
    print("[database] Tables to create:", [table.name for table in Base.metadata.sorted_tables])
    Base.metadata.create_all(bind=engine)
    print("[database] Database initialized successfully")
