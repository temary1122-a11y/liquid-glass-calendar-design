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


# ────────────────────────────────────────────────────────────
# Контекстный менеджер подключения
# ────────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    """Возвращает соединение с автокоммитом/откатом."""
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
            conn.executescript("""
                -- Рабочие дни
                CREATE TABLE IF NOT EXISTS work_days (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_date  TEXT    UNIQUE NOT NULL,   -- YYYY-MM-DD
                    is_closed INTEGER NOT NULL DEFAULT 0 -- 0 = открыт, 1 = закрыт
                );

                -- Временные слоты
                CREATE TABLE IF NOT EXISTS time_slots (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_date  TEXT    NOT NULL,           -- YYYY-MM-DD
                    slot_time TEXT    NOT NULL,           -- HH:MM
                    is_booked INTEGER NOT NULL DEFAULT 0, -- 0 = свободен, 1 = занят
                    UNIQUE(day_date, slot_time),
                    FOREIGN KEY (day_date) REFERENCES work_days(day_date) ON DELETE CASCADE
                );

                -- Записи клиентов
                CREATE TABLE IF NOT EXISTS bookings (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER NOT NULL,
                    username     TEXT,
                    client_name  TEXT    NOT NULL,
                    phone        TEXT    NOT NULL,
                    day_date     TEXT    NOT NULL,
                    slot_time    TEXT    NOT NULL,
                    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                    is_cancelled INTEGER NOT NULL DEFAULT 0,
                    cancel_reason TEXT,
                    cancelled_at TEXT,
                    UNIQUE(day_date, slot_time)
                );

                -- Миграция: открываем все закрытые дни по умолчанию
                UPDATE work_days SET is_closed = 0 WHERE is_closed = 1;

                -- Миграция: добавляем service_id в bookings если нет
                ALTER TABLE bookings ADD COLUMN service_id TEXT;

                -- Миграция: добавляем is_cancelled в bookings если нет
                ALTER TABLE bookings ADD COLUMN is_cancelled INTEGER NOT NULL DEFAULT 0;

                -- Миграция: добавляем cancel_reason в bookings если нет
                ALTER TABLE bookings ADD COLUMN cancel_reason TEXT;

                -- Миграция: добавляем cancelled_at в bookings если нет
                ALTER TABLE bookings ADD COLUMN cancelled_at TEXT;
            """)
    except sqlite3.OperationalError:
        # Игнорируем ошибку если колонка уже существует
        pass
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
    """Возвращает доступные рабочие дни для клиентов (только будущие и открытые)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM work_days WHERE day_date >= date('now','localtime') AND is_closed = 0 ORDER BY day_date"
        ).fetchall()


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
    """Добавляет слот в рабочий день. True = успех."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO time_slots (day_date, slot_time) VALUES (?, ?)",
                (day_date, slot_time)
            )
            logger.info(f"Слот добавлен: {day_date} {slot_time}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Слот {day_date} {slot_time} уже существует")
        return False
    except Exception as e:
        logger.error(f"Ошибка добавления слота {day_date} {slot_time}: {e}")
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
    with get_conn() as conn:
        return conn.execute("""
            SELECT ts.*
            FROM time_slots ts
            JOIN work_days wd ON wd.day_date = ts.day_date
            WHERE ts.day_date = ?
              AND ts.is_booked = 0
              AND wd.is_closed = 0
            ORDER BY ts.slot_time
        """, (day_date,)).fetchall()


def get_all_slots(day_date: str) -> list[sqlite3.Row]:
    """Все слоты на день (для просмотра в админке)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM time_slots WHERE day_date = ? ORDER BY slot_time",
            (day_date,)
        ).fetchall()


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
    """Обновляет запись клиента."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
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
