// ============================================================
// src/components/ClientProfile.tsx — Личный кабинет клиента
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, Clock, X, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';
import { apiClient, type UserBooking } from '../api/client';
import { vibrateMedium, vibrateSuccess, vibrateError } from '../utils/vibration';
import ConfirmModal from './ConfirmModal';

interface ClientProfileProps {
  userId: number | null;
  onHasActiveBooking: (hasBooking: boolean) => void;
  onBookingCancelled: () => void;
}

function formatDate(dateStr: string): string {
  try {
    const [, month, day] = dateStr.split('-').map(Number);
    const months = [
      'янв', 'фев', 'мар', 'апр', 'май', 'июн',
      'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
    ];
    return `${day}.${String(month).padStart(2, '0')} ${months[month - 1]}`;
  } catch {
    return dateStr;
  }
}

function formatDateTime(dateStr: string, timeStr: string): string {
  try {
    const [, month, day] = dateStr.split('-').map(Number);
    return `${String(day).padStart(2, '0')}.${String(month).padStart(2, '0')} ${timeStr}`;
  } catch {
    return `${dateStr} ${timeStr}`;
  }
}

function getStatusBadge(booking: UserBooking) {
  if (booking.is_cancelled) {
    return { label: 'отменена', className: 'badge-cancelled' };
  }
  switch (booking.status) {
    case 'confirmed':
      return { label: 'подтверждена', className: 'badge-confirmed' };
    case 'pending':
      return { label: 'ожидает', className: 'badge-pending' };
    case 'completed':
      return { label: 'завершена', className: 'badge-completed' };
    case 'cancelled':
      return { label: 'отменена', className: 'badge-cancelled' };
    default:
      return { label: booking.status, className: 'badge-pending' };
  }
}

function isActiveBooking(booking: UserBooking): boolean {
  return !booking.is_cancelled && booking.status !== 'cancelled' && booking.status !== 'completed';
}

export default function ClientProfile({
  userId,
  onHasActiveBooking,
  onBookingCancelled,
}: ClientProfileProps) {
  const [bookings, setBookings] = useState<UserBooking[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  const activeBooking = bookings.find(isActiveBooking) || null;
  const historyBookings = bookings.filter((b) => !isActiveBooking(b));

  const loadBookings = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const data = await apiClient.getUserBookings(userId);
      setBookings(data);
      const hasActive = data.some(isActiveBooking);
      onHasActiveBooking(hasActive);
    } catch {
      console.error('Failed to load bookings');
    } finally {
      setIsLoading(false);
    }
  }, [userId, onHasActiveBooking]);

  useEffect(() => {
    loadBookings();
  }, [loadBookings]);

  const handleCancelClick = (bookingId: number) => {
    vibrateMedium();
    setCancellingId(bookingId);
    setConfirmOpen(true);
  };

  const handleConfirmCancel = async () => {
    if (!cancellingId || !userId) return;
    setIsCancelling(true);
    setConfirmOpen(false);

    try {
      const result = await apiClient.cancelBookingByUser(
        cancellingId,
        'Отменено клиентом через Mini App',
        userId
      );

      if (result.success) {
        vibrateSuccess();
        // Notify admin
        const booking = bookings.find((b) => b.id === cancellingId);
        if (booking) {
          await apiClient.notifyCancellation({
            client_name: booking.client_name,
            slot_time: booking.slot_time,
            day_date: booking.day_date,
            reason: 'Отменено клиентом через Mini App',
          });
        }
        await loadBookings();
        onBookingCancelled();
      } else {
        vibrateError();
        alert(result.message || 'Ошибка отмены записи');
      }
    } catch {
      vibrateError();
      alert('Ошибка соединения с сервером');
    } finally {
      setIsCancelling(false);
      setCancellingId(null);
    }
  };

  // No user — nothing to show
  if (!userId) return null;

  // Loading state
  if (isLoading) {
    return (
      <div className="mb-4">
        <div className="liquid-glass rounded-2xl p-4 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-[#c4967a]/30 border-t-[#c4967a] rounded-full spinner" />
          <p className="text-sm text-[#9e8476]">Загрузка записей...</p>
        </div>
      </div>
    );
  }

  // No active booking and no history — hide
  if (!activeBooking && historyBookings.length === 0) return null;

  return (
    <>
      <ConfirmModal
        isOpen={confirmOpen}
        title="Отменить запись?"
        message="Вы уверены, что хотите отменить запись к мастеру?"
        warning="Предоплата сгорит при отмене записи"
        confirmText="Да, отменить"
        cancelText="Нет, оставить"
        onConfirm={handleConfirmCancel}
        onCancel={() => {
          setConfirmOpen(false);
          setCancellingId(null);
        }}
        danger
      />

      <div className="mb-4 space-y-3">
        {/* ── Active Booking Block ── */}
        <AnimatePresence>
          {activeBooking && (
            <motion.div
              key="active-booking"
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12, scale: 0.97 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="liquid-glass rounded-2xl p-4 border border-emerald-200/40">
                {/* Header */}
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-xl bg-emerald-100 flex items-center justify-center">
                    <CheckCircle2 size={15} className="text-emerald-600" />
                  </div>
                  <span className="text-sm font-semibold text-[#3d2b1f]">Вы записаны</span>
                  <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${getStatusBadge(activeBooking).className}`}>
                    {getStatusBadge(activeBooking).label}
                  </span>
                </div>

                {/* Date & Time */}
                <div className="flex items-center gap-4 mb-3 p-3 rounded-xl bg-white/30">
                  <div className="flex items-center gap-2">
                    <Calendar size={14} className="text-[#c4967a]" />
                    <span className="text-sm text-[#3d2b1f] font-medium">
                      {formatDate(activeBooking.day_date)}
                    </span>
                  </div>
                  <div className="w-px h-4 bg-[#c4967a]/20" />
                  <div className="flex items-center gap-2">
                    <Clock size={14} className="text-[#c4967a]" />
                    <span className="text-sm text-[#3d2b1f] font-medium">
                      {activeBooking.slot_time}
                    </span>
                  </div>
                </div>

                {/* Cancel button */}
                <button
                  onClick={() => handleCancelClick(activeBooking.id)}
                  disabled={isCancelling}
                  className="w-full py-2.5 rounded-xl border border-red-200/60 text-red-500 text-sm font-medium
                    bg-red-50/50 hover:bg-red-50 transition-all active:scale-98 disabled:opacity-50
                    flex items-center justify-center gap-2"
                >
                  {isCancelling ? (
                    <>
                      <div className="w-4 h-4 border-2 border-red-300 border-t-red-500 rounded-full spinner" />
                      Отменяем...
                    </>
                  ) : (
                    <>
                      <X size={15} />
                      Отменить запись
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── History Block ── */}
        {historyBookings.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            <button
              onClick={() => {
                vibrateLight();
                setShowHistory((v) => !v);
              }}
              className="w-full liquid-glass-calendar rounded-2xl p-3.5 flex items-center justify-between
                transition-all active:scale-99"
            >
              <div className="flex items-center gap-2">
                <Calendar size={15} className="text-[#9e8476]" />
                <span className="text-sm font-medium text-[#3d2b1f]">
                  История записей
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-[#c4967a]/15 text-[#c4967a] font-medium">
                  {historyBookings.length}
                </span>
              </div>
              {showHistory ? (
                <ChevronUp size={16} className="text-[#9e8476]" />
              ) : (
                <ChevronDown size={16} className="text-[#9e8476]" />
              )}
            </button>

            <AnimatePresence>
              {showHistory && (
                <motion.div
                  key="history"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden"
                >
                  <div className="pt-2 space-y-2">
                    {historyBookings.map((b) => {
                      const badge = getStatusBadge(b);
                      return (
                        <motion.div
                          key={b.id}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="liquid-glass-calendar rounded-xl p-3 flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <div className="text-center">
                              <p className="text-xs font-semibold text-[#3d2b1f]">
                                {formatDateTime(b.day_date, b.slot_time)}
                              </p>
                              {b.cancel_reason && (
                                <p className="text-[10px] text-[#9e8476] mt-0.5 max-w-[140px] truncate">
                                  {b.cancel_reason}
                                </p>
                              )}
                            </div>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.className}`}>
                            {badge.label}
                          </span>
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </>
  );
}

// Need to import this locally to avoid circular
function vibrateLight() {
  const haptic = window.Telegram?.WebApp?.HapticFeedback;
  if (haptic) {
    haptic.impactOccurred('light');
  } else if (navigator.vibrate) {
    navigator.vibrate(8);
  }
}
