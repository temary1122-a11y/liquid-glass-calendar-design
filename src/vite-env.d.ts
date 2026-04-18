/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Backend Configuration
  readonly VITE_BACKEND_URL?: string;

  // Social Media Links
  readonly VITE_PRICES_POST_LINK?: string;
  readonly VITE_INSTAGRAM_LINK?: string;

  // Bot Configuration
  readonly VITE_BOT_TOKEN?: string;
  readonly VITE_ADMIN_ID?: string;
  readonly VITE_ADMIN_USERNAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Telegram WebApp types
interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

interface TelegramWebApp {
  initDataUnsafe: {
    user?: TelegramUser;
    query_id?: string;
    auth_date?: number;
    hash?: string;
  };
  ready: () => void;
  expand: () => void;
  close: () => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

export {};
