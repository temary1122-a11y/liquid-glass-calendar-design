import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Text, ForeignKey, UniqueConstraint, Index
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
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    slots = relationship(
        "TimeSlot",
        back_populates="work_day",
        cascade="all, delete-orphan",
        order_by="TimeSlot.time",
    )


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    day_id = Column(Integer, ForeignKey("work_days.id", ondelete="CASCADE"))
    time = Column(String(5), nullable=False)  # HH:MM
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    work_day = relationship("WorkDay", back_populates="slots")
    booking = relationship(
        "Booking",
        back_populates="slot",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("day_id", "time", name="unique_day_time"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(
        Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), unique=True
    )
    user_id = Column(Integer, nullable=True)
    username = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled, completed
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    slot = relationship("TimeSlot", back_populates="booking")

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
    Base.metadata.create_all(bind=engine)
