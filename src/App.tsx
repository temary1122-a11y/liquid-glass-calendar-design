import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Settings, Calendar as CalendarIcon } from 'lucide-react';
import Calendar from './components/Calendar';
import AdminSchedulePanel from './components/AdminSchedulePanel';
import { SOCIAL_LINKS, BOT_CONFIG } from './config';
import { vibrateMedium } from './utils/vibration';

// ─── View type ────────────────────────────────────────────────────────────────
type View = 'client' | 'admin';

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [view, setView] = useState<View>('client');
  const [isAdmin, setIsAdmin] = useState(false);

  // Проверяем admin_id из Telegram WebApp initData
  useEffect(() => {
    // Проверяем параметр URL ?admin=true
    const urlParams = new URLSearchParams(window.location.search);
    const isAdminParam = urlParams.get('admin') === 'true';

    // Инициализируем Telegram WebApp
    const tg = (window as any).Telegram?.WebApp;
    console.log('=== Telegram WebApp Debug ===');
    console.log('Telegram.WebApp exists:', !!tg);
    console.log('Telegram.WebApp object:', tg);
    console.log('Telegram.WebApp.version:', tg?.version);
    console.log('Telegram.WebApp.platform:', tg?.platform);
    console.log('HapticFeedback available:', !!tg?.HapticFeedback);
    console.log('HapticFeedback object:', tg?.HapticFeedback);
    console.log('initDataUnsafe:', tg?.initDataUnsafe);
    console.log('initData:', tg?.initData);
    console.log('user from initDataUnsafe:', tg?.initDataUnsafe?.user);
    console.log('user from initData:', tg?.initDataUser);
    console.log('URL param admin:', isAdminParam);
    console.log('User Agent:', navigator.userAgent);

    if (tg) {
      tg.ready();
      tg.expand();
    }

    // Если есть параметр ?admin=true - считаем админом
    if (isAdminParam) {
      console.log('Admin mode via URL parameter');
      setIsAdmin(true);
      setView('admin');
      return;
    }

    // Получаем user_id из Telegram WebApp
    // Проверяем оба источника: initDataUnsafe и initData
    const user = tg?.initDataUnsafe?.user || tg?.initDataUser;

    if (user) {
      const userId = user.id;
      const adminId = parseInt(BOT_CONFIG.ADMIN_ID);
      const isAdminUser = userId === adminId;

      console.log('User ID:', userId);
      console.log('Admin ID:', adminId);
      console.log('Is admin:', isAdminUser);

      setIsAdmin(isAdminUser);
      // Если не админ, сбрасываем view на client
      if (!isAdminUser) {
        setView('client');
      }
    } else {
      // Если Telegram WebApp недоступен или нет user - считаем клиентом
      // Это может быть если открыли в обычном браузере
      console.log('No user data found, treating as client');
      setIsAdmin(false);
      setView('client');
    }
  }, []);

  // Устанавливаем background image
  useEffect(() => {
    document.body.style.backgroundImage = 'url(/background.jpg)';
    document.body.style.backgroundSize = 'cover';
    document.body.style.backgroundPosition = 'center';
  }, []);

  // Сбрасываем background при размонтировании
  useEffect(() => {
    return () => {
      document.body.style.backgroundImage = '';
    };
  }, []);

  return (
    <div className="min-h-screen safe-bottom">
      {/* ── Decorative background blobs ── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden>
        <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full
          bg-[#f7d5bc]/40 blur-[80px]" />
        <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full
          bg-[#e8c9b0]/35 blur-[80px]" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-60 h-60 rounded-full
          bg-[#fde8d5]/30 blur-[60px]" />
      </div>

      {/* ── Main content ── */}
      <div className="relative z-10 max-w-sm mx-auto px-3 pt-4 pb-8">

        {/* ── App header ── */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <span className="text-2xl select-none sticker-bounce" aria-hidden>🎀</span>
            <div>
              <h1 className="text-[#3d2b1f] text-lg font-semibold leading-tight">
                YourLashes
              </h1>
              <p className="text-[#9e8476] text-sm">
                {view === 'client' ? 'Запись онлайн' : 'Режим мастера'}
              </p>
            </div>
          </div>

          {/* View toggle button - только для админа */}
          {isAdmin && (
            <motion.button
              whileTap={{ scale: 0.90 }}
              onClick={() => {
                vibrateMedium();
                setView(v => v === 'client' ? 'admin' : 'client');
              }}
              className="liquid-glass-nav w-11 h-11 flex items-center justify-center rounded-2xl
                text-[#a07060] hover:text-[#7c5340] transition-colors duration-200"
              title={view === 'client' ? 'Режим мастера' : 'Режим клиента'}
            >
              {view === 'client'
                ? <Settings size={18} strokeWidth={2} />
                : <CalendarIcon size={18} strokeWidth={2} />
              }
            </motion.button>
          )}
        </div>

        {/* ── View subtitle ── */}
        <AnimatePresence mode="wait">
          {view === 'client' && (
            <motion.div
              key="client-header"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.20 }}
              className="mb-4 px-1"
            >
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-[#c4967a]" />
                <p className="text-[#9e8476] text-xs">
                  Выберите удобное время для записи
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Main panel ── */}
        <AnimatePresence mode="wait">
          {view === 'client' ? (
            <motion.div
              key="client"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              <Calendar />

              {/* ── Social links buttons (always visible in client view) ── */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="mt-4 space-y-3"
              >
                {/* Prices button */}
                <a
                  href={SOCIAL_LINKS.PRICES_POST_LINK}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full p-3 liquid-glass-calendar rounded-xl hover:bg-white/50 transition-all duration-200 text-center"
                >
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-lg font-semibold text-[#3d2b1f]">💰 Прайсы</span>
                  </div>
                  <p className="text-sm text-[#9e8476] mt-1">Посмотреть цены на услуги</p>
                </a>

                {/* Instagram button */}
                <a
                  href="https://www.instagram.com/your_lashes_simf?igsh=MTFvaHdscnIzbWF0Mw%3D%3D&utm_source=qr"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full p-3 liquid-glass-calendar rounded-xl hover:bg-white/50 transition-all duration-200 text-center"
                >
                  <div className="flex items-center justify-center gap-1">
                    <span className="text-xl">📸</span>
                    <span className="text-sm font-semibold text-[#3d2b1f]">Instagram</span>
                  </div>
                </a>
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="admin"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              <AdminSchedulePanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
