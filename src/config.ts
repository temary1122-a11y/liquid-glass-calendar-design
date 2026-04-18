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
  ADMIN_CONFIRMATION: (data: { name: string; date: string; time: string; service: string; address: string }) =>
    `Здравствуйте, ${data.name}!

Ваша запись на ${data.date} в ${data.time} подтверждена.

Адрес: ${data.address}
Телефон: +7 (999) 123-45-67

До встречи!`,

  // Форма для заполнения данных клиента при записи
  CLIENT_BOOKING_FORM: (data: { name: string; phone: string; date: string; time: string }) =>
    `📋 <b>Новая запись</b>

👤 <b>Имя:</b> ${data.name}
📞 <b>Телефон:</b> ${data.phone}
📅 <b>Дата:</b> ${data.date}
🕐 <b>Время:</b> ${data.time}

Подтвердить запись?`,

  // Быстрый ответ администратора при подтверждении записи
  ADMIN_QUICK_REPLY: (data: { name: string; date: string; time: string }) =>
    `✅ <b>Запись подтверждена!</b>

👤 ${data.name}
📅 ${data.date} в ${data.time}

Ждём вас! Если нужно отменить — напишите нам.`,

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
  ADDRESS: 'г. Москва, ул. Примерная, д. 1',
  PHONE: '+7 (999) 123-45-67',
  TELEGRAM_USERNAME: '@yourusername',
};

// ── Ссылки на соцсети и посты ─────────────────────────────────
export const SOCIAL_LINKS = {
  // Ссылка на пост с прайсами в группе
  PRICES_POST_LINK: import.meta.env.VITE_PRICES_POST_LINK || 'https://t.me/lashessoto4ka/285',

  // Ссылка на TikTok
  TIKTOK_LINK: import.meta.env.VITE_TIKTOK_LINK || 'https://tiktok.com/@yourusername',

  // Ссылка на Instagram
  INSTAGRAM_LINK: import.meta.env.VITE_INSTAGRAM_LINK || 'https://instagram.com/yourusername',

  // Ссылка на портфолио
  PORTFOLIO_LINK: 'https://ru.pinterest.com/crystalwithluv/_created/',
};

// ── Настройки интерфейса ───────────────────────────────────────
export const UI_CONFIG = {
  VISIBLE_SLOTS: 3,
  MAX_VISIBLE_DAYS: 30,
  DEFAULT_TIME_SLOTS: [
    '09:00', '10:30', '12:00', '13:30',
    '15:00', '16:30', '18:00', '19:30',
  ],
};

// ── Токен и ID администратора (для интеграции с ботом) ──────────
export const BOT_CONFIG = {
  // Telegram Bot Token (получить у @BotFather)
  BOT_TOKEN: import.meta.env.VITE_BOT_TOKEN || '',

  // ID администратора (получить у @userinfobot)
  ADMIN_ID: import.meta.env.VITE_ADMIN_ID || '8736987138',

  // ID канала для обязательной подписки
  CHANNEL_ID: import.meta.env.VITE_CHANNEL_ID || '@your_channel',

  // ID канала для публикации расписания
  SCHEDULE_CHANNEL_ID: import.meta.env.VITE_SCHEDULE_CHANNEL_ID || '@your_schedule_channel',
};
