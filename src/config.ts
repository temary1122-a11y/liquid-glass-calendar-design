// ============================================================
// src/config.ts — Корневой файл конфигурации
// ============================================================
// Основной файл для быстрой настройки всех параметров приложения:
// - Шаблоны сообщений
// - Контактная информация
// - Ссылки на соцсети и посты
// - Настройки интерфейса
// ============================================================

// ── Шаблоны сообщений ──────────────────────────────────────────
export const MESSAGE_TEMPLATES = {
  // Подтверждение записи клиенту
  ADMIN_CONFIRMATION: (data: { date: string; time: string }) =>
    `Записала 💌
📆: ${data.date}
🟣: ${data.time}
📎Адрес: Тихий переулок, 4
🤩3 этаж, первая дверь справа 🤩`,

  // Форма для заполнения данных клиента при записи
  CLIENT_BOOKING_FORM: (data: { name: string; phone: string; date: string; time: string }) =>
    `📋 <b>Новая запись</b>

👤 <b>Имя:</b> ${data.name}
📞 <b>Телефон:</b> ${data.phone}
📅 <b>Дата:</b> ${data.date}
🕐 <b>Время:</b> ${data.time}

Подтвердить запись?`,

  // Уведомление об отмене записи
  BOOKING_CANCELLED: (data: { name: string; date: string; time: string }) =>
    `❌ <b>Запись отменена</b>

👤 ${data.name}
📅 ${data.date} в ${data.time}

Будем рады видеть вас снова!`,

  // Напоминание о записи
  BOOKING_REMINDER: (data: { name: string; date: string; time: string; address: string }) =>
    `🔔 <b>Напоминание о записи</b>

Здравствуйте, ${data.name}!

Напоминаем, что ваша запись завтра:
📅 ${data.date}
🕐 ${data.time}

Адрес: ${data.address}

До встречи!`,
};

// ── Контактная информация ───────────────────────────────────────
export const CONTACT_INFO = {
  ADMIN_USERNAME: import.meta.env.VITE_ADMIN_USERNAME || '@SotkaLashes',
};

// ── Ссылки на соцсети и посты ─────────────────────────────────
export const SOCIAL_LINKS = {
  // Ссылка на пост с прайсами в группе
  PRICES_POST_LINK: import.meta.env.VITE_PRICES_POST_LINK || 'https://t.me/lashessoto4ka/285',

  // Ссылка на Instagram
  INSTAGRAM_LINK: import.meta.env.VITE_INSTAGRAM_LINK || 'https://www.instagram.com/your_lashes_simf?igsh=MTFvaHdscnIzbWF0Mw%3D%3D&utm_source=qr',

  // Ссылка на портфолио
  PORTFOLIO_LINK: 'https://ru.pinterest.com/crystalwithluv/_created/',
};

// ── Настройки интерфейса ───────────────────────────────────────
export const UI_CONFIG = {
  VISIBLE_SLOTS: 3,
  MAX_VISIBLE_DAYS: 30,
};

// ── Backend API URL ─────────────────────────────────────────────
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'https://liquid-glass-calendar-design.onrender.com';

// ── Токен и ID администратора (для интеграции с ботом) ──────────
export const BOT_CONFIG = {
  // Telegram Bot Token (получить у @BotFather)
  BOT_TOKEN: import.meta.env.VITE_BOT_TOKEN || '',

  // ID администратора (получить у @userinfobot)
  ADMIN_ID: import.meta.env.VITE_ADMIN_ID || '',

  // Секретный ключ для HMAC аутентификации (генерируйте случайную строку)
  ADMIN_SECRET_KEY: import.meta.env.VITE_ADMIN_SECRET_KEY || '',
};
