# ============================================================
# database/db.py — Инициализация БД и все SQL-операции
# ============================================================

import sqlite3
import logging
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional

from config import DB_PATH

logger = logging.getLogger(__name__)

# PostgreSQL support
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("Using PostgreSQL database")
else:
    logger.info(f"Using SQLite database at {DB_PATH}")


# ────────────────────────────────────────────────────────────
# Контекстный менеджер подключения
# ────────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    """Возвращает соединение с автокоммитом/откатом."""
    if USE_POSTGRES:
        # PostgreSQL connection
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    else:
        # SQLite connection
        # Создаём директорию если не существует
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ────────────────────────────────────────────────────────────
# Создание таблиц
# ────────────────────────────────────────────────────────────
def init_db() -> None:
    """Создаёт все нужные таблицы, если они не существуют."""
    try:
        with get_conn() as conn:
            if USE_POSTGRES:
                # PostgreSQL schema
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS work_days (
                        id        SERIAL PRIMARY KEY,
                        day_date  TEXT    UNIQUE NOT NULL,
                        is_closed INTEGER NOT NULL DEFAULT 0
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS time_slots (
                        id        SERIAL PRIMARY KEY,
                        day_date  TEXT    NOT NULL,
                        slot_time TEXT    NOT NULL,
                        is_booked INTEGER NOT NULL DEFAULT 0,
                        UNIQUE(day_date, slot_time),
                        FOREIGN KEY (day_date) REFERENCES work_days(day_date) ON DELETE CASCADE
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        id           SERIAL PRIMARY KEY,
                        user_id      INTEGER,
                        username     TEXT,
                        client_name  TEXT    NOT NULL,
                        phone        TEXT    NOT NULL,
                        day_date     TEXT    NOT NULL,
                        slot_time    TEXT    NOT NULL,
                        created_at   TEXT    NOT NULL DEFAULT NOW(),
                        is_cancelled INTEGER NOT NULL DEFAULT 0,
                        cancel_reason TEXT,
                        cancelled_at TEXT,
                        service_id   TEXT,
                        note         TEXT,
                        UNIQUE(day_date, slot_time)
                    );
                """)
            else:
                # SQLite schema
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS work_days (
                        id        INTEGER PRIMARY KEY AUTOINCREMENT,
                        day_date  TEXT    UNIQUE NOT NULL,
                        is_closed INTEGER NOT NULL DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS time_slots (
                        id        INTEGER PRIMARY KEY AUTOINCREMENT,
                        day_date  TEXT    NOT NULL,
                        slot_time TEXT    NOT NULL,
                        is_booked INTEGER NOT NULL DEFAULT 0,
                        UNIQUE(day_date, slot_time),
                        FOREIGN KEY (day_date) REFERENCES work_days(day_date) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS bookings (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id      INTEGER,
                        username     TEXT,
                        client_name  TEXT    NOT NULL,
                        phone        TEXT    NOT NULL,
                        day_date     TEXT    NOT NULL,
                        slot_time    TEXT    NOT NULL,
                        created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                        is_cancelled INTEGER NOT NULL DEFAULT 0,
                        cancel_reason TEXT,
                        cancelled_at TEXT,
                        service_id   TEXT,
                        note         TEXT,
                        UNIQUE(day_date, slot_time)
                    );
                """)
    except Exception as e:
        if USE_POSTGRES:
            # PostgreSQL might raise duplicate column error
            if "duplicate column" in str(e).lower():
                logger.info(f"Column already exists: {e}")
            else:
                logger.error(f"Error initializing database: {e}")
                raise
        else:
            # SQLite might raise OperationalError for duplicate columns
            if "duplicate column" in str(e).lower():
                logger.info(f"Column already exists: {e}")
            else:
                logger.error(f"Error initializing database: {e}")
                raise
    logger.info("БД инициализирована.")


# ────────────────────────────────────────────────────────────
# Рабочие дни
# ────────────────────────────────────────────────────────────
def add_work_day(day_date: str, time_slots: list[str] | None = None) -> bool:
    """
    Добавляет рабочий день и (опционально) временные слоты.
    Возвращает True если день добавлен, False если уже существует.
    """
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO work_days (day_date) VALUES (?)",
                (day_date,)
            )
            if time_slots:
                conn.executemany(
                    "INSERT OR IGNORE INTO time_slots (day_date, slot_time) VALUES (?, ?)",
                    [(day_date, t) for t in time_slots]
                )
            logger.info(f"Рабочий день добавлен: {day_date}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Рабочий день {day_date} уже существует")
        return False
    except Exception as e:
        logger.error(f"Ошибка добавления рабочего дня {day_date}: {e}")
        return False


def close_day(day_date: str) -> None:
    """Закрывает рабочий день (все слоты становятся недоступны)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE work_days SET is_closed = 1 WHERE day_date = ?",
            (day_date,)
        )


def open_day(day_date: str) -> None:
    """Открывает ранее закрытый рабочий день."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE work_days SET is_closed = 0 WHERE day_date = ?",
            (day_date,)
        )


def get_available_days() -> list[sqlite3.Row]:
    """Возвращает открытые рабочие дни с хотя бы одним свободным слотом."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT DISTINCT wd.day_date
            FROM work_days wd
            JOIN time_slots ts ON ts.day_date = wd.day_date
            WHERE wd.is_closed = 0
              AND ts.is_booked = 0
              AND wd.day_date >= date('now', 'localtime')
            ORDER BY wd.day_date
        """).fetchall()


def get_all_work_days() -> list[sqlite3.Row]:
    """Возвращает все рабочие дни (для админ-панели)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM work_days ORDER BY day_date"
        ).fetchall()


def get_available_work_days() -> list[sqlite3.Row]:
    """Returns available work days for clients (only future, open, and with free slots)."""
    logger.info("get_available_work_days() called - fetching available work days")
    with get_conn() as conn:
        result = conn.execute("""
            SELECT DISTINCT wd.*
            FROM work_days wd
            JOIN time_slots ts ON ts.day_date = wd.day_date
            WHERE wd.day_date >= date('now','localtime')
              AND wd.is_closed = 0
              AND ts.is_booked = 0
            ORDER BY wd.day_date
        """).fetchall()
        logger.info(f"get_available_work_days() returned {len(result)} days")
        return result


def day_exists(day_date: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM work_days WHERE day_date = ?", (day_date,)
        ).fetchone()
        return row is not None


# ────────────────────────────────────────────────────────────
# Временные слоты
# ────────────────────────────────────────────────────────────
def add_time_slot(day_date: str, slot_time: str) -> bool:
    """Adds slot to work day. Auto-creates work day if needed. True = success."""
    try:
        with get_conn() as conn:
            # First, ensure work day exists
            conn.execute(
                "INSERT OR IGNORE INTO work_days (day_date, is_closed) VALUES (?, 0)",
                (day_date,)
            )
            
            # Then add the slot
            conn.execute(
                "INSERT INTO time_slots (day_date, slot_time) VALUES (?, ?)",
                (day_date, slot_time)
            )
            logger.info(f"Slot added: {day_date} {slot_time}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Slot {day_date} {slot_time} already exists")
        return False
    except Exception as e:
        logger.error(f"Error adding slot {day_date} {slot_time}: {e}")
        return False


def delete_time_slot(day_date: str, slot_time: str) -> bool:
    """Удаляет слот (только если он не забронирован). True = успех."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT is_booked FROM time_slots WHERE day_date=? AND slot_time=?",
                (day_date, slot_time)
            ).fetchone()
            if row is None:
                logger.warning(f"Слот {day_date} {slot_time} не найден")
                return False
            if row["is_booked"]:
                logger.warning(f"Слот {day_date} {slot_time} занят, нельзя удалить")
                return False
            conn.execute(
                "DELETE FROM time_slots WHERE day_date=? AND slot_time=?",
                (day_date, slot_time)
            )
            logger.info(f"Слот удален: {day_date} {slot_time}")
            return True
    except Exception as e:
        logger.error(f"Ошибка удаления слота {day_date} {slot_time}: {e}")
        return False


def delete_work_day(day_date: str) -> bool:
    """Удаляет рабочий день со всеми слотами. True = успех."""
    try:
        with get_conn() as conn:
            # Сначала удаляем все слоты этого дня
            conn.execute("DELETE FROM time_slots WHERE day_date=?", (day_date,))
            # Затем удаляем сам рабочий день
            cursor = conn.execute("DELETE FROM work_days WHERE day_date=?", (day_date,))
            if cursor.rowcount > 0:
                logger.info(f"Рабочий день удален: {day_date}")
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка удаления рабочего дня {day_date}: {e}")
        return False


def get_free_slots(day_date: str) -> list[sqlite3.Row]:
    """Возвращает свободные слоты на указанный день."""
    logger.info(f"get_free_slots() called for day={day_date}")
    with get_conn() as conn:
        result = conn.execute("""
            SELECT ts.*
            FROM time_slots ts
            JOIN work_days wd ON wd.day_date = ts.day_date
            WHERE ts.day_date = ?
              AND ts.is_booked = 0
              AND wd.is_closed = 0
            ORDER BY ts.slot_time
        """, (day_date,)).fetchall()
        logger.info(f"get_free_slots() returned {len(result)} slots for day={day_date}")
        return result


def get_all_slots(day_date: str) -> list[sqlite3.Row]:
    """Все слоты на день (для просмотра в админке)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM time_slots WHERE day_date = ? ORDER BY slot_time",
            (day_date,)
        ).fetchall()


def update_slot_time(old_date: str, old_time: str, new_date: str, new_time: str) -> bool:
    """Обновляет время слота (для редактирования пустого слота без клиента)."""
    try:
        with get_conn() as conn:
            # Проверяем что слот существует и не забронирован
            existing = conn.execute(
                "SELECT * FROM time_slots WHERE day_date = ? AND slot_time = ? AND is_booked = 0",
                (old_date, old_time)
            ).fetchone()

            if not existing:
                logger.warning(f"Slot not found or already booked: {old_date} {old_time}")
                return False

            # Проверяем что новый слот не существует
            conflict = conn.execute(
                "SELECT * FROM time_slots WHERE day_date = ? AND slot_time = ?",
                (new_date, new_time)
            ).fetchone()

            if conflict:
                logger.warning(f"Target slot already exists: {new_date} {new_time}")
                return False

            # Обновляем время слота
            conn.execute(
                "UPDATE time_slots SET day_date = ?, slot_time = ? WHERE day_date = ? AND slot_time = ?",
                (new_date, new_time, old_date, old_time)
            )
            conn.commit()
            logger.info(f"Slot time updated: {old_date} {old_time} -> {new_date} {new_time}")
            return True
    except Exception as e:
        logger.error(f"Error updating slot time: {e}")
        return False


# ────────────────────────────────────────────────────────────
# Helper функции
# ────────────────────────────────────────────────────────────
def _release_slot(day_date: str, slot_time: str) -> bool:
    """
    Освобождает слот (помечает как свободный).
    Внутренняя helper функция с error handling и логированием.
    """
    try:
        with get_conn() as conn:
            conn.execute(
                "UPDATE time_slots SET is_booked=0 WHERE day_date=? AND slot_time=?",
                (day_date, slot_time)
            )
            logger.info(f"Слот освобожден: {day_date} {slot_time}")
            return True
    except Exception as e:
        logger.error(f"Ошибка освобождения слота {day_date} {slot_time}: {e}")
        return False


# ────────────────────────────────────────────────────────────
# Записи клиентов
# ────────────────────────────────────────────────────────────
def create_booking(
    user_id: int,
    username: Optional[str],
    client_name: str,
    phone: str,
    day_date: str,
    slot_time: str,
    service_id: Optional[str] = None,
) -> Optional[int]:
    """
    Создаёт запись клиента.
    Возвращает booking_id или None если слот уже занят.
    """
    try:
        with get_conn() as conn:
            # Проверяем, не занят ли слот
            slot = conn.execute(
                "SELECT is_booked FROM time_slots WHERE day_date=? AND slot_time=?",
                (day_date, slot_time)
            ).fetchone()
            if slot is None or slot["is_booked"]:
                logger.warning(f"Слот {day_date} {slot_time} недоступен для записи")
                return None

            cursor = conn.execute(
                """INSERT INTO bookings
                   (user_id, username, client_name, phone, day_date, slot_time, service_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, client_name, phone, day_date, slot_time, service_id)
            )
            booking_id = cursor.lastrowid
            # Помечаем слот как занятый
            conn.execute(
                "UPDATE time_slots SET is_booked=1 WHERE day_date=? AND slot_time=?",
                (day_date, slot_time)
            )
            logger.info(f"Запись создана: user_id={user_id}, {day_date} {slot_time}")
            return booking_id
    except sqlite3.IntegrityError as e:
        logger.error(f"IntegrityError при создании записи: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка создания записи: {e}")
        return None


def get_user_booking(user_id: int) -> Optional[sqlite3.Row]:
    """Возвращает активную запись пользователя (если есть)."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT b.*
            FROM bookings b
            JOIN work_days wd ON wd.day_date = b.day_date
            WHERE b.user_id = ?
              AND b.day_date >= date('now', 'localtime')
            ORDER BY b.day_date, b.slot_time
            LIMIT 1
        """, (user_id,)).fetchone()


def cancel_booking_by_user(user_id: int) -> Optional[sqlite3.Row]:
    """
    Отменяет запись пользователя.
    Возвращает данные отменённой записи или None.
    """
    try:
        with get_conn() as conn:
            booking = conn.execute("""
                SELECT * FROM bookings
                WHERE user_id = ?
                  AND day_date >= date('now', 'localtime')
                ORDER BY day_date, slot_time
                LIMIT 1
            """, (user_id,)).fetchone()
            if booking is None:
                logger.warning(f"Нет активной записи для пользователя {user_id}")
                return None
            
            conn.execute("DELETE FROM bookings WHERE id=?", (booking["id"],))
            _release_slot(booking["day_date"], booking["slot_time"])
            logger.info(f"Запись пользователя {user_id} отменена")
            return booking
    except Exception as e:
        logger.error(f"Ошибка отмены записи пользователя {user_id}: {e}")
        return None


def cancel_booking_by_id(booking_id: int, reason: Optional[str] = None) -> Optional[sqlite3.Row]:
    """
    Отменяет запись по ID (для администратора).
    Если указана reason, сохраняет причину отмены вместо удаления записи.
    """
    try:
        with get_conn() as conn:
            booking = conn.execute(
                "SELECT * FROM bookings WHERE id=?", (booking_id,)
            ).fetchone()
            if booking is None:
                logger.warning(f"Запись с ID {booking_id} не найдена")
                return None

            if reason:
                # Помечаем запись как отмененную с причиной
                conn.execute(
                    """UPDATE bookings
                       SET is_cancelled = 1,
                           cancel_reason = ?,
                           cancelled_at = datetime('now')
                       WHERE id = ?""",
                    (reason, booking_id)
                )
                _release_slot(booking["day_date"], booking["slot_time"])
                logger.info(f"Запись {booking_id} отменена с причиной: {reason}")
            else:
                # Удаляем запись полностью (старое поведение)
                conn.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
                _release_slot(booking["day_date"], booking["slot_time"])
                logger.info(f"Запись {booking_id} удалена")
            return booking
    except Exception as e:
        logger.error(f"Ошибка отмены записи {booking_id}: {e}")
        return None


def get_bookings_for_day(day_date: str) -> list[sqlite3.Row]:
    """Все записи на указанный день."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE day_date=? ORDER BY slot_time",
            (day_date,)
        ).fetchall()


def get_booking_by_id(booking_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE id=?", (booking_id,)
        ).fetchone()


def get_all_future_bookings() -> list[sqlite3.Row]:
    """Все будущие записи (для восстановления задач APScheduler)."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM bookings
            WHERE day_date >= date('now', 'localtime')
            ORDER BY day_date, slot_time
        """).fetchall()


def get_booking_history() -> list[sqlite3.Row]:
    """Все записи (включая отмененные) для анализа трафика."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM bookings
            ORDER BY day_date DESC, slot_time DESC
        """).fetchall()


def get_cancelled_bookings() -> list[sqlite3.Row]:
    """Только отмененные записи с причинами."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM bookings
            WHERE cancelled_at IS NOT NULL
            ORDER BY day_date DESC, slot_time DESC
        """).fetchall()


def update_booking(
    booking_id: int,
    client_name: str,
    phone: str,
    day_date: str,
    slot_time: str,
    username: Optional[str] = None,
    note: Optional[str] = None,
) -> Optional[sqlite3.Row]:
    """Обновляет запись клиента и обновляет статус слотов."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            
            # Получаем текущую информацию о записи
            current_booking = get_booking_by_id(booking_id)
            if not current_booking:
                logger.error(f"Запись {booking_id} не найдена")
                return None
            
            old_date = current_booking["day_date"]
            old_time = current_booking["slot_time"]
            
            # Если время изменилось, обновляем статусы слотов
            if old_date != day_date or old_time != slot_time:
                # Освобождаем старый слот
                conn.execute(
                    "UPDATE time_slots SET is_booked=0 WHERE day_date=? AND slot_time=?",
                    (old_date, old_time)
                )
                
                # Занимаем новый слот
                conn.execute(
                    "UPDATE time_slots SET is_booked=1 WHERE day_date=? AND slot_time=?",
                    (day_date, slot_time)
                )
                logger.info(f"Слоты обновлены: {old_date} {old_time} -> {day_date} {slot_time}")
            
            # Обновляем запись клиента
            cursor.execute("""
                UPDATE bookings
                SET client_name=?, phone=?, day_date=?, slot_time=?, username=?, note=?
                WHERE id=?
            """, (client_name, phone, day_date, slot_time, username, note, booking_id))
            conn.commit()
            logger.info(f"Запись обновлена: booking_id={booking_id}")
            return get_booking_by_id(booking_id)
    except Exception as e:
        logger.error(f"Ошибка обновления записи {booking_id}: {e}")
        return None


def delete_booking(day_date: str, slot_time: str) -> bool:
    """Удаляет запись полностью (для админ панели)."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM bookings WHERE day_date=? AND slot_time=?
            """, (day_date, slot_time))
            conn.commit()
            if cursor.rowcount > 0:
                _release_slot(day_date, slot_time)
                logger.info(f"Запись удалена: {day_date} {slot_time}")
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка удаления записи {day_date} {slot_time}: {e}")
        return False


def user_has_active_booking(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя активная запись."""
    return get_user_booking(user_id) is not None


def get_all_clients() -> list[sqlite3.Row]:
    """Все клиенты с их записями для админки (сортировка по новизне)."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT b.id, b.user_id, b.username, b.client_name, b.phone,
                   b.day_date, b.slot_time, b.created_at, b.is_cancelled,
                   b.cancel_reason, b.cancelled_at
            FROM bookings b
            ORDER BY b.created_at DESC
        """).fetchall()
