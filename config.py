# ============================================================
# config.py — Конфигурация бота
# ============================================================

import os
from dotenv import load_dotenv

# Загружаем .env если он существует (для локальной разработки)
# На Railway переменные окружения устанавливаются напрямую
load_dotenv()

# ── Токен бота (получить у @BotFather) ──────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Если токен не найден, пробуем прочитать из .env файла напрямую
if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('BOT_TOKEN='):
                    BOT_TOKEN = line.split('=', 1)[1].strip()
                    break
    except:
        pass

# ── ID администратора (ваш Telegram user_id) ────────────────
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "8736987138"))

# ── Канал с расписанием (например: @my_channel или -100xxxxxxxxxx) ─
SCHEDULE_CHANNEL_ID: str = os.getenv("SCHEDULE_CHANNEL_ID", "@your_schedule_channel")

# ── Канал для обязательной подписки ─────────────────────────
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "@your_channel")          # username или числовой ID
CHANNEL_LINK: str = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")

# ── Путь к базе данных SQLite ────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "lash_bot.db")

# ── Прайс-лист (HTML) ────────────────────────────────────────
PRICE_TEXT: str = (
    "💅 <b>Прайс-лист на наращивание ресниц</b>\n\n"
    "╔══════════════════════════╗\n"
    "║  <b>2D</b>  —  <b>2 000 руб.</b>           ║\n"
    "║  <b>3D</b>  —  <b>2 500 руб.</b>           ║\n"
    "╚══════════════════════════╝\n\n"
    "✨ В стоимость входит:\n"
    "• Подбор изгиба и длины\n"
    "• Профессиональные материалы\n"
    "• Коррекция формы\n\n"
    "📞 Для уточнения деталей — записывайтесь через бота!"
)

# ── Ссылка на портфолио ──────────────────────────────────────
PORTFOLIO_LINK: str = "https://ru.pinterest.com/crystalwithluv/_created/"

# ── Ссылка на пост с прайсами в группе ────────────────────────
PRICES_POST_LINK: str = os.getenv("PRICES_POST_LINK", "https://t.me/lashessoto4ka/285")

# ── Ссылки на социальные сети ────────────────────────────────
TIKTOK_LINK: str = os.getenv("TIKTOK_LINK", "https://tiktok.com/@yourusername")
INSTAGRAM_LINK: str = os.getenv("INSTAGRAM_LINK", "https://instagram.com/yourusername")

# ── Рабочие часы по умолчанию (используются при инициализации) ─
DEFAULT_TIME_SLOTS: list[str] = [
    "09:00", "10:30", "12:00", "13:30",
    "15:00", "16:30", "18:00", "19:30",
]

# ── Горизонт записи (дней вперёд) ────────────────────────────
BOOKING_HORIZON_DAYS: int = 30
