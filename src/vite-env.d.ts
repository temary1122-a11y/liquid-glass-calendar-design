/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string;
  readonly VITE_WS_URL: string;
  readonly VITE_ADMIN_ID: string;
  readonly VITE_BOT_USERNAME: string;
  readonly VITE_ADMIN_SECRET_KEY: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Telegram Web App types
interface TelegramWebAppUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

interface TelegramWebAppInitData {
  user?: TelegramWebAppUser;
  chat_instance?: string;
  chat_type?: string;
  auth_date?: number;
  hash?: string;
}

interface TelegramWebApp {
  ready: () => void;
  expand: () => void;
  close: () => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback: (ok: boolean) => void) => void;
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
  initData: string;
  initDataUnsafe: TelegramWebAppInitData;
  colorScheme: 'light' | 'dark';
  themeParams: Record<string, string>;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  platform: string;
  version: string;
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isProgressVisible: boolean;
    isActive: boolean;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: (leaveActive?: boolean) => void;
    hideProgress: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    setText: (text: string) => void;
  };
  BackButton: {
    isVisible: boolean;
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
  openLink: (url: string) => void;
  openTelegramLink: (url: string) => void;
}

interface Window {
  Telegram?: {
    WebApp: TelegramWebApp;
  };
}
