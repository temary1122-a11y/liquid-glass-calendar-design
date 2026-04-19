# ============================================================
# config.py — Конфигурация бота
# ============================================================

import os
from dotenv import load_dotenv

# Загружаем .env если он существует (для локальной разработки)
# На Render переменные окружения устанавливаются напрямую
import pathlib
env_path = pathlib.Path(__file__).parent / '.env'
env_local_path = pathlib.Path(__file__).parent / '.env.local'
load_dotenv(dotenv_path=env_path)
load_dotenv(dotenv_path=env_local_path, override=True)

# ── Валидация секретов ────────────────────────────────────────
def validate_config():
    """Валидация обязательных переменных окружения"""
    required_vars = ['BOT_TOKEN', 'ADMIN_ID', 'ADMIN_SECRET_KEY']
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == "":
            raise ValueError(
                f"❌ Переменная {var} не установлена или пуста. "
                f"Пожалуйста, проверьте файл .env"
            )

    try:
        admin_id = int(os.getenv('ADMIN_ID'))
    except ValueError:
        raise ValueError("❌ ADMIN_ID должно быть целым числом")

    return admin_id

# Валидируем конфигурацию при импорте
ADMIN_ID = validate_config()

# ── Секретный ключ для HMAC аутентификации ───────────────────
ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "").strip()

# ── Mini App URL ─────────────────────────────────────────────
MINI_APP_URL: str = os.getenv("MINI_APP_URL", "https://liquid-glass-calendar-design.vercel.app")

# ── Токен бота (получить у @BotFather) ──────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# ── Юзернейм администратора (для редиректа в личку) ───────────
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "@SotkaLashes")

# ── Путь к базе данных SQLite ────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "lash_bot.db")

# ── Адрес салона ─────────────────────────────────────────────
ADDRESS: str = os.getenv("ADDRESS", "Тихий переулок, 4")

# ── Ссылка на портфолио ──────────────────────────────────────
PORTFOLIO_LINK: str = os.getenv("PORTFOLIO_LINK", "https://ru.pinterest.com/crystalwithluv/_created/")

# ── Ссылка на пост с прайсами в группе ────────────────────────
PRICES_POST_LINK: str = os.getenv("PRICES_POST_LINK", "https://t.me/lashessoto4ka/285")

# ── Ссылка на Instagram ─────────────────────────────────────
INSTAGRAM_LINK: str = os.getenv("INSTAGRAM_LINK", "https://www.instagram.com/your_lashes_simf?igsh=MTFvaHdscnIzbWF0Mw%3D%3D&utm_source=qr")
