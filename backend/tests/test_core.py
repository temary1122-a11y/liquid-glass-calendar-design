"""
Core logic tests — business rules, edge cases, and regression fixes.

Run:
  cd backend && python -m pytest tests/test_core.py -v

Uses an in-memory SQLite database — no external dependencies needed.
"""

import sys
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BOT_TOKEN"] = "test"
os.environ["ADMIN_ID"] = "123"

from database.db import Base, Booking, TimeSlot, WorkDay
from services.admin_command import (_execute_book, _execute_cancel, _execute_check,
                                     _execute_set_day_status, _pretty_date)
from utils.crypto import encrypt_phone, decrypt_phone


@pytest.fixture(scope="function")
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _add_work_day(db: Session, date_str: str, is_closed: bool = False,
                  slots: list[str] | None = None) -> WorkDay:
    wd = WorkDay(day_date=date_str, is_closed=1 if is_closed else 0)
    db.add(wd)
    if slots:
        for t in slots:
            db.add(TimeSlot(day_date=date_str, slot_time=t, is_booked=0))
    db.commit()
    return wd


# ── 1. Duplicate booking — the month-later bugfix ──

class TestDuplicateBooking:
    def test_same_date_blocked(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00", "11:00"])
        b1 = Booking(user_id=111, client_name="Алина", day_date=today,
                     slot_time="10:00", status="pending",
                     created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b1)
        s1 = db_session.query(TimeSlot).filter(
            TimeSlot.day_date == today, TimeSlot.slot_time == "10:00").first()
        s1.is_booked = 1
        db_session.commit()
        dup = db_session.query(Booking).filter(
            Booking.user_id == 111,
            Booking.status.notin_(["cancelled", "completed"]),
            Booking.day_date == today).first()
        assert dup is not None

    def test_different_date_allowed(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        nw = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        _add_work_day(db_session, nw, slots=["12:00"])
        b1 = Booking(user_id=222, client_name="Света", day_date=today,
                     slot_time="10:00", status="confirmed",
                     created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b1); s=db_session.query(TimeSlot).filter(
            TimeSlot.day_date==today,TimeSlot.slot_time=="10:00").first(); s.is_booked=1; db_session.commit()
        exists = db_session.query(Booking).filter(
            Booking.user_id==222, Booking.status.notin_(["cancelled","completed"]),
            Booking.day_date==nw).first()
        assert exists is None  # different date = allowed


# ── 2. Cancel frees slot ──

class TestCancel:
    def test_frees_slot(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        b = Booking(user_id=444, client_name="Оля", day_date=today,
                    slot_time="10:00", status="pending",
                    created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b); s=db_session.query(TimeSlot).filter(
            TimeSlot.day_date==today,TimeSlot.slot_time=="10:00").first(); s.is_booked=1; db_session.commit()
        assert s.is_booked==1
        b.status="cancelled"; b.cancelled_at=datetime.now(timezone.utc).isoformat(); s.is_booked=0; db_session.commit()
        assert b.status=="cancelled"; assert s.is_booked==0

    def test_cancelled_not_active(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        b = Booking(user_id=555, client_name="Катя", day_date=today,
                    slot_time="10:00", status="cancelled",
                    created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b); db_session.commit()
        active = db_session.query(Booking).filter(
            Booking.user_id==555, Booking.status.notin_(["cancelled","completed"])).all()
        assert len(active)==0


# ── 3. Auto-complete ──

class TestAutoComplete:
    def test_past_completes(self, db_session):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        _add_work_day(db_session, yesterday, slots=["10:00"])
        b = Booking(user_id=666, client_name="Настя", day_date=yesterday,
                    slot_time="10:00", status="confirmed",
                    created_at=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat())
        db_session.add(b); db_session.commit()
        today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for b in db_session.query(Booking).filter(
                Booking.day_date<today, Booking.status.in_(["pending","confirmed"])).all():
            b.status="completed"
        db_session.commit()
        b = db_session.query(Booking).filter(Booking.id==b.id).first()
        assert b.status=="completed"


# ── 4. Phone encryption ──

class TestPhoneEncryption:
    def test_roundtrip(self):
        p="+79161234567"
        e=encrypt_phone(p)
        d=decrypt_phone(e)
        assert d==p
    def test_none(self):
        assert encrypt_phone(None) is None
        assert decrypt_phone(None) is None
    def test_empty(self):
        assert encrypt_phone("")==""
        assert decrypt_phone("")==""


# ── 5. Admin commands (with test db session) ──

class TestAdminCommands:
    def test_check_empty_day(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00","11:00"])
        cmd = {"action":"check","client_name":None,"date":today,"time":None,"reason":None,"confidence":"high"}
        r = _execute_check(db_session, cmd)
        assert "свободно" in r and "10:00" in r

    def test_check_with_booking(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        b = Booking(user_id=888, client_name="Лена", day_date=today,
                    slot_time="10:00", status="confirmed",
                    created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b); s=db_session.query(TimeSlot).filter(
            TimeSlot.day_date==today,TimeSlot.slot_time=="10:00").first(); s.is_booked=1; db_session.commit()
        r = _execute_check(db_session, {"action":"check","date":today,"time":None,"client_name":None,"reason":None,"confidence":"high"})
        assert "Лена" in r and "10:00" in r

    def test_check_closed_day(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, is_closed=True)
        r = _execute_check(db_session, {"action":"check","date":today,"time":None,"client_name":None,"reason":None,"confidence":"high"})
        assert "выходной" in r.lower()

    def test_check_no_slots(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=[])
        r = _execute_check(db_session, {"action":"check","date":today,"time":None,"client_name":None,"reason":None,"confidence":"high"})
        assert "нет" in r.lower()

    def test_book_creates_slot_and_booking(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        r = _execute_book(db_session, {"action":"book","client_name":"Алина","date":today,"time":"10:00","reason":None,"confidence":"high"})
        assert "Алина" in r and "✅" in r
        b = db_session.query(Booking).filter(Booking.client_name=="Алина").first()
        assert b is not None and b.status=="confirmed"
        s = db_session.query(TimeSlot).filter(TimeSlot.day_date==today,TimeSlot.slot_time=="10:00").first()
        assert s.is_booked==1

    def test_book_occupied_slot(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        b = Booking(client_name="Маша", day_date=today, slot_time="10:00",
                    status="confirmed", created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b); s=db_session.query(TimeSlot).filter(
            TimeSlot.day_date==today,TimeSlot.slot_time=="10:00").first(); s.is_booked=1; db_session.commit()
        r = _execute_book(db_session, {"action":"book","client_name":"Алина","date":today,"time":"10:00","reason":None,"confidence":"high"})
        assert "занято" in r.lower() and "Маша" in r

    def test_set_day_off(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today)
        r = _execute_set_day_status(db_session, {"action":"set_day_off","date":today}, closed=True)
        wd = db_session.query(WorkDay).filter(WorkDay.day_date==today).first()
        assert wd.is_closed==1

    def test_set_day_on(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, is_closed=True)
        _execute_set_day_status(db_session, {"action":"set_day_on","date":today}, closed=False)
        wd = db_session.query(WorkDay).filter(WorkDay.day_date==today).first()
        assert wd.is_closed==0

    def test_set_day_off_cancels_bookings(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        b = Booking(user_id=999, client_name="Анна", day_date=today, slot_time="10:00",
                    status="confirmed", created_at=datetime.now(timezone.utc).isoformat())
        db_session.add(b); s=db_session.query(TimeSlot).filter(
            TimeSlot.day_date==today,TimeSlot.slot_time=="10:00").first(); s.is_booked=1; db_session.commit()
        r = _execute_set_day_status(db_session, {"action":"set_day_off","date":today}, closed=True)
        b2 = db_session.query(Booking).filter(Booking.id==b.id).first()
        assert b2.status == "cancelled"


# ── 6. Unique constraints ──

class TestConstraints:
    def test_duplicate_slot(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        _add_work_day(db_session, today, slots=["10:00"])
        with pytest.raises(Exception):
            db_session.add(TimeSlot(day_date=today, slot_time="10:00", is_booked=0))
            db_session.commit()

    def test_duplicate_workday(self, db_session):
        today = datetime.now().strftime("%Y-%m-%d")
        db_session.add(WorkDay(day_date=today, is_closed=0)); db_session.commit()
        with pytest.raises(Exception):
            db_session.add(WorkDay(day_date=today, is_closed=0)); db_session.commit()


# ── 7. Config centralization ──

class TestConfig:
    def test_imports(self):
        from config import BOT_TOKEN, ADMIN_ID_INT, ADMIN_ID, DATABASE_URL
        assert BOT_TOKEN is not None and ADMIN_ID_INT is not None


# ── 8. Regex fallback ──

class TestRegex:
    def test_book(self):
        from services.groq_client import _fallback_regex_extraction
        c = _fallback_regex_extraction("Запиши Алину на 12:00 21 числа")
        assert c["action"]=="book" and c["time"]=="12:00"

    def test_cancel(self):
        from services.groq_client import _fallback_regex_extraction
        c = _fallback_regex_extraction("Отмени запись Светы")
        assert c["action"]=="cancel"

    def test_check(self):
        from services.groq_client import _fallback_regex_extraction
        c = _fallback_regex_extraction("Кто записан 21 числа?")
        assert c["action"]=="check"

    def test_unknown(self):
        from services.groq_client import _fallback_regex_extraction
        c = _fallback_regex_extraction("блабла как дела")
        assert c["action"]=="unknown"

    def test_today(self):
        from services.groq_client import _fallback_regex_extraction
        c = _fallback_regex_extraction("Покажи записи на сегодня")
        assert c["date"]==datetime.now().strftime("%Y-%m-%d")

    def test_tomorrow(self):
        from services.groq_client import _fallback_regex_extraction
        c = _fallback_regex_extraction("Запиши Машу на завтра в 15:00")
        assert c["date"]==(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")


# ── 9. Pretty date ──

class TestPrettyDate:
    def test_today(self):
        assert "Сегодня" in _pretty_date(datetime.now().strftime("%Y-%m-%d"))
    def test_tomorrow(self):
        assert "Завтра" in _pretty_date((datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d"))
    def test_future(self):
        d = (datetime.now()+timedelta(days=5)).strftime("%Y-%m-%d")
        assert "20" in _pretty_date(d)
