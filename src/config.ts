// ============================================================
// src/config.ts — Конфигурация приложения
// ============================================================

export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  'https://liquid-glass-calendar-design.onrender.com';

export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  'wss://liquid-glass-calendar-design.onrender.com/ws';

export const BOT_CONFIG = {
  ADMIN_ID: import.meta.env.VITE_ADMIN_ID || '1834686956',
  BOT_TOKEN: '8646567713:AAGaYReANb-Ua4NSoHIOlk06GKKExL-DS6M',
  BOT_USERNAME: import.meta.env.VITE_BOT_USERNAME || 'YourLashesBot',
};

export const ADMIN_SECRET_KEY =
  import.meta.env.VITE_ADMIN_SECRET_KEY || 'default-secret';

export const CONTACT_INFO = {
  ADMIN_USERNAME: '@SotkaLashes',
  ADDRESS: 'Тихий переулок, 4',
  PHONE: '+7 978 423-74-53',
};

export const SOCIAL_LINKS = {
  PRICES_POST_LINK: 'https://t.me/lashessoto4ka/285',
  INSTAGRAM_LINK:
    'https://www.instagram.com/your_lashes_simf?igsh=MTFvaHdscnIzbWF0Mw%3D%3D&utm_source=qr',
};

export const MESSAGE_TEMPLATES = {
  CLIENT_BOOKING_FORM: ({
    name,
    phone,
    date,
    time,
  }: {
    name: string;
    phone?: string;
    date: string;
    time: string;
  }): string => {
    let message = `здравствуйте! Запишите, пожалуйста\n👤 Имя: ${name}`;
    if (phone && phone.trim()) {
      message += `\n📞 Телефон: ${phone}`;
    }
    message += `\n📅 Дата: ${date}\n🕐 Время: ${time}`;
    return message;
  },
};

export const SERVICES = [
  { id: 'classic', name: 'Классические ресницы', price: 2000 },
  { id: 'volume', name: 'Объемные ресницы', price: 3000 },
  { id: '2d', name: '2D эффект', price: 3500 },
  { id: '3d', name: '3D эффект', price: 4000 },
  { id: 'removal', name: 'Снятие ресниц', price: 500 },
];
