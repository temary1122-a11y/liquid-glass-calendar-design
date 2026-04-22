// ============================================================
// src/App.tsx — Главный компонент приложения
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Settings, Calendar as CalendarIcon, Wifi, WifiOff } from 'lucide-react';
import Calendar from './components/Calendar';
import AdminSchedulePanel from './components/AdminSchedulePanel';
import ClientProfile from './components/ClientProfile';
import { SOCIAL_LINKS, BOT_CONFIG } from './config';
import { vibrateMedium, vibrateLight } from './utils/vibration';
import { useWebSocket } from './hooks/useWebSocket';

type View = 'client' | 'admin';

export default function App() {
  const [view, setView] = useState<View>('client');
  const [isAdmin, setIsAdmin] = useState(false);
  const [userId, setUserId] = useState<number | null>(null);
  const [hasActiveBooking, setHasActiveBooking] = useState(false);
  const [bookingRefreshKey, setBookingRefreshKey] = useState(0);

  const wsUrl = import.meta.env.VITE_WS_URL || 'wss://liquid-glass-calendar-design.onrender.com/ws';
  const { isConnected } = useWebSocket(wsUrl);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const isAdminParam = urlParams.get('admin') === 'true';

    const tg = window.Telegram?.WebApp;

    if (tg) {
      tg.ready();
      tg.expand();
    }

    const user = tg?.initDataUnsafe?.user;

    if (user) {
      setUserId(user.id);
      // Check if user is admin
      const adminId = parseInt(BOT_CONFIG.ADMIN_ID);
      setIsAdmin(user.id === adminId);
      
      // Only set admin view if user is admin OR admin param is true (for testing)
      if (isAdminParam || user.id === adminId) {
        setView('admin');
      }
    }
  }, []);

  const handleHasActiveBooking = useCallback((hasBooking: boolean) => {
    setHasActiveBooking(hasBooking);
  }, []);

  const handleBookingCancelled = useCallback(() => {
    setHasActiveBooking(false);
    setBookingRefreshKey((k) => k + 1);
  }, []);

  const handleBookingCreated = useCallback(() => {
    setBookingRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="min-h-screen safe-bottom">
      {/* Ambient background blobs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden>
        <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full
          bg-[#f7d5bc]/40 blur-[80px]" />
        <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full
          bg-[#e8c9b0]/35 blur-[80px]" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-60 h-60 rounded-full
          bg-[#fde8d5]/30 blur-[60px]" />
      </div>

      <div className="relative z-10 max-w-sm mx-auto px-3 pt-4 pb-8">
        {/* ── Header ── */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <span className="text-2xl select-none sticker-bounce" aria-hidden>🎀</span>
            <div>
              <h1 className="text-[#3d2b1f] text-xl font-semibold leading-tight">
                YourLashes
              </h1>
              <p className="text-[#9e8476] text-sm">
                {view === 'client' ? 'Запись онлайн' : 'Режим мастера'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Connection indicator */}
            <div className="flex items-center gap-1">
              {isConnected ? (
                <Wifi size={12} className="text-emerald-500" />
              ) : (
                <WifiOff size={12} className="text-[#9e8476]/40" />
              )}
            </div>

            {/* Admin toggle */}
            {isAdmin && (
              <motion.button
                whileTap={{ scale: 0.90 }}
                onClick={() => {
                  vibrateMedium();
                  setView((v) => (v === 'client' ? 'admin' : 'client'));
                }}
                className="liquid-glass-nav w-11 h-11 flex items-center justify-center rounded-2xl
                  text-[#a07060] hover:text-[#7c5340] transition-colors duration-200"
                aria-label={view === 'client' ? 'Перейти в режим мастера' : 'Перейти к записи'}
              >
                {view === 'client' ? (
                  <Settings size={18} strokeWidth={2} />
                ) : (
                  <CalendarIcon size={18} strokeWidth={2} />
                )}
              </motion.button>
            )}
          </div>
        </div>

        {/* ── Client header hint ── */}
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

        {/* ── Main Content ── */}
        <AnimatePresence mode="wait">
          {view === 'client' ? (
            <motion.div
              key="client"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* Client profile / active booking block */}
              <ClientProfile
                key={bookingRefreshKey}
                userId={userId}
                onHasActiveBooking={handleHasActiveBooking}
                onBookingCancelled={handleBookingCancelled}
              />

              {/* Calendar */}
              <Calendar
                hasActiveBooking={hasActiveBooking}
                onBookingCreated={handleBookingCreated}
              />

              {/* Social links */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="mt-4 space-y-3"
              >
                <a
                  href={SOCIAL_LINKS.PRICES_POST_LINK}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => vibrateLight()}
                  className="block w-full p-3 liquid-glass-calendar rounded-xl
                    hover:bg-white/50 transition-all duration-200 text-center active:scale-98"
                >
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-lg font-semibold text-[#3d2b1f]">💰 Прайсы</span>
                  </div>
                  <p className="text-sm text-[#9e8476] mt-1">Посмотреть цены на услуги</p>
                </a>

                <a
                  href={SOCIAL_LINKS.INSTAGRAM_LINK}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => vibrateLight()}
                  className="block w-full p-3 liquid-glass-calendar rounded-xl
                    hover:bg-white/50 transition-all duration-200 text-center active:scale-98"
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
