# 🚀 Deployment Guide

## Backend (Render)

### Переменные окружения

Установите следующие переменные окружения в Render Dashboard:

**Обязательные:**
- `BOT_TOKEN` - Токен Telegram бота (от @BotFather)
- `ADMIN_ID` - Ваш Telegram User ID (от @userinfobot)
- `ADMIN_SECRET_KEY` - Секретный ключ для HMAC аутентификации (сгенерируйте: `python generate_secret_key.py`)
- `ADMIN_USERNAME` - Ваш Telegram username (с @)
- `DB_PATH` - Путь к базе данных (например: `/etc/secrets/lash_bot.db`)

**Опциональные:**
- `FRONTEND_URL` - URL фронтенда (например: `https://liquid-glass-calendar-design.vercel.app`)
- `BACKEND_URL` - URL бэкенда (автоматически устанавливается Render)
- `WS_URL` - WebSocket URL (например: `wss://liquid-glass-calendar-design.onrender.com/ws`)
- `INSTAGRAM_LINK` - Ссылка на Instagram

### Деплой

1. Подключите репозиторий к Render
2. Создайте новый Web Service
3. Выберите `Existing Dockerfile` или `Build from source`
4. Установите Runtime: `Python 3.12`
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `python start_all.py`
7. Добавьте переменные окружения
8. Deploy

---

## Frontend (Vercel)

### Переменные окружения

Установите следующие переменные окружения в Vercel Project Settings:

**Обязательные:**
- `VITE_BACKEND_URL` - URL бэкенда (например: `https://liquid-glass-calendar-design.onrender.com`)
- `VITE_ADMIN_ID` - Ваш Telegram User ID
- `VITE_ADMIN_SECRET_KEY` - Секретный ключ для HMAC аутентификации (тот же что на бэкенде)
- `VITE_BOT_TOKEN` - Токен Telegram бота (для интеграции)

**Опциональные:**
- `VITE_PRICES_POST_LINK` - Ссылка на пост с ценами
- `VITE_INSTAGRAM_LINK` - Ссылка на Instagram

### Деплой

1. Подключите репозиторий к Vercel
2. Framework Preset: `Vite`
3. Build Command: `npm run build`
4. Output Directory: `dist`
5. Install Command: `npm install`
6. Добавьте переменные окружения
7. Deploy

---

## Telegram Bot

### Webhook

После деплоя бэкенда установите webhook:

```bash
curl -F "url=https://your-backend.onrender.com/webhook" \
     -F "secret_token=your_secret" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

---

## Проверка после деплоя

### Backend

1. Проверьте health endpoint: `https://your-backend.onrender.com/`
2. Проверьте admin endpoint с HMAC аутентификацией

### Frontend

1. Откройте Mini App в Telegram
2. Проверьте что данные загружаются
3. Проверьте админ панель

---

## Безопасность

- ✅ Хардкоды убраны
- ✅ HMAC аутентификация для admin routes
- ✅ Rate limiting включен
- ✅ CORS настроен
- ⚠️ В продакшене укажите конкретные домены в CORS вместо `*`

---

## Troubleshooting

### Backend не запускается

- Проверьте логи в Render Dashboard
- Убедитесь что все переменные окружения установлены
- Проверьте что Python версия 3.12

### Frontend не подключается к backend

- Проверьте `VITE_BACKEND_URL` в Vercel
- Проверьте CORS настройки на бэкенде
- Проверьте что backend запущен и доступен

### HMAC аутентификация не работает

- Убедитесь что `ADMIN_SECRET_KEY` одинаковый на бэкенде и фронтенде
- Проверьте что `ADMIN_ID` правильный
