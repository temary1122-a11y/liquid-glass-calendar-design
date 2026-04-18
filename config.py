# ============================================================
# config.py — Конфигурация бота
# ============================================================

import os
from dotenv import load_dotenv

# Загружаем .env если он существует (для локальной разработки)
# На Render переменные окружения устанавливаются напрямую
load_dotenv()

# ── Mini App URL ─────────────────────────────────────────────
MINI_APP_URL: str = "https://liquid-glass-calendar-design.vercel.app"

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
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "1834686956"))

# ── Путь к базе данных SQLite ────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "lash_bot.db")

# ── Адрес салона ─────────────────────────────────────────────
ADDRESS: str = "Тихий переулок, 4"

# ── Ссылка на портфолио ──────────────────────────────────────
PORTFOLIO_LINK: str = "https://ru.pinterest.com/crystalwithluv/_created/"

# ── Ссылка на пост с прайсами в группе ────────────────────────
PRICES_POST_LINK: str = os.getenv("PRICES_POST_LINK", "https://t.me/lashessoto4ka/285")

# ── Ссылка на Instagram ─────────────────────────────────────
INSTAGRAM_LINK: str = os.getenv("INSTAGRAM_LINK", "https://www.instagram.com/your_lashes_simf?igsh=MTFvaHdscnIzbWF0Mw%3D%3D&utm_source=qr")
