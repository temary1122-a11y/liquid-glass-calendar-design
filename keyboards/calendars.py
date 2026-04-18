# ============================================================
# keyboards/calendars.py — Inline-календарь
# ============================================================

from datetime import date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель",
    "Май", "Июнь", "Июль", "Август", "Сентябрь",
    "Октябрь", "Ноябрь", "Декабрь",
]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def build_calendar(
    available_dates: set[str],
    year: int | None = None,
    month: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Строит inline-календарь.
    available_dates — множество строк 'YYYY-MM-DD' доступных дат.
    """
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    builder = InlineKeyboardBuilder()

    # ── Заголовок: «← Месяц Год →» ──────────────────────────
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal_prev:{year}:{month}"),
        InlineKeyboardButton(
            text=f"{MONTHS_RU[month]} {year}",
            callback_data="cal_ignore"
        ),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_next:{year}:{month}"),
    )

    # ── Дни недели ───────────────────────────────────────────
    builder.row(*[
        InlineKeyboardButton(text=d, callback_data="cal_ignore")
        for d in WEEKDAYS_RU
    ])

    # ── Дни месяца ───────────────────────────────────────────
    first_day = date(year, month, 1)
    # Начинаем с понедельника
    start = first_day - timedelta(days=first_day.weekday())

    row_buttons: list[InlineKeyboardButton] = []
    current = start

    while True:
        if current.month > month and current.year >= year:
            break
        if current.month == month and current.year == year:
            day_str = current.strftime("%Y-%m-%d")
            if day_str in available_dates and current >= today:
                # ✅ Доступная дата
                btn = InlineKeyboardButton(
                    text=f"🟢 {current.day}",
                    callback_data=f"cal_day:{day_str}"
                )
            else:
                # Недоступная дата
                btn = InlineKeyboardButton(
                    text=str(current.day),
                    callback_data="cal_ignore"
                )
        else:
            # Дни другого месяца — пустые
            btn = InlineKeyboardButton(text=" ", callback_data="cal_ignore")

        row_buttons.append(btn)
        if len(row_buttons) == 7:
            builder.row(*row_buttons)
            row_buttons = []
        current += timedelta(days=1)

    if row_buttons:
        # Дополняем последнюю строку пустыми кнопками
        while len(row_buttons) < 7:
            row_buttons.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
        builder.row(*row_buttons)

    # ── Кнопка «Назад» ──────────────────────────────────────
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )

    return builder.as_markup()


def build_admin_calendar(
    all_dates: set[str],
    year: int | None = None,
    month: int | None = None,
) -> InlineKeyboardMarkup:
    """Календарь для админ-панели — показывает все рабочие дни."""
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"adm_cal_prev:{year}:{month}"),
        InlineKeyboardButton(
            text=f"{MONTHS_RU[month]} {year}",
            callback_data="cal_ignore"
        ),
        InlineKeyboardButton(text="▶️", callback_data=f"adm_cal_next:{year}:{month}"),
    )
    builder.row(*[
        InlineKeyboardButton(text=d, callback_data="cal_ignore")
        for d in WEEKDAYS_RU
    ])

    first_day = date(year, month, 1)
    start = first_day - timedelta(days=first_day.weekday())
    row_buttons: list[InlineKeyboardButton] = []
    current = start

    while True:
        if current.month > month and current.year >= year:
            break
        if current.month == month and current.year == year:
            day_str = current.strftime("%Y-%m-%d")
            if day_str in all_dates:
                btn = InlineKeyboardButton(
                    text=f"📅 {current.day}",
                    callback_data=f"adm_day:{day_str}"
                )
            else:
                btn = InlineKeyboardButton(
                    text=str(current.day),
                    callback_data=f"adm_empty_day:{day_str}"
                )
        else:
            btn = InlineKeyboardButton(text=" ", callback_data="cal_ignore")

        row_buttons.append(btn)
        if len(row_buttons) == 7:
            builder.row(*row_buttons)
            row_buttons = []
        current += timedelta(days=1)

    if row_buttons:
        while len(row_buttons) < 7:
            row_buttons.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text="🔙 Админ-меню", callback_data="admin_menu")
    )

    return builder.as_markup()
