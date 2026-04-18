# ============================================================
# states.py — FSM-состояния бота
# ============================================================

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния процесса записи клиента."""
    choosing_date = State()      # Выбор даты в календаре
    choosing_time = State()      # Выбор временного слота
    entering_name = State()      # Ввод имени
    entering_phone = State()     # Ввод номера телефона
    confirming = State()         # Подтверждение записи


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    menu = State()               # Главное меню администратора

    # Работа с днями
    add_day_input = State()      # Ввод даты нового рабочего дня
    add_day_slots = State()      # Ввод слотов для нового дня
    choosing_day_to_close = State()   # Выбор дня для закрытия
    choosing_day_to_open = State()    # Выбор дня для открытия

    # Работа со слотами
    choosing_day_add_slot = State()   # Выбор дня для добавления слота
    add_slot_time_input = State()     # Ввод времени нового слота
    choosing_day_del_slot = State()   # Выбор дня для удаления слота

    # Просмотр расписания
    choosing_day_view = State()       # Выбор дня для просмотра

    # Отмена записи
    cancel_booking_input = State()    # Ввод ID записи для отмены
