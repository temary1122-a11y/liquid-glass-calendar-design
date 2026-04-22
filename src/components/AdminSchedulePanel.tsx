// ============================================================
// src/components/AdminSchedulePanel.tsx — Панель управления для мастера
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { format, isSameMonth, isToday, startOfMonth, endOfMonth, eachDayOfInterval, startOfWeek, endOfWeek, isBefore, startOfDay } from 'date-fns';
import { ru } from 'date-fns/locale';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSwipeable } from 'react-swipeable';
import { apiClient, type AdminWorkDay, type UserBooking } from '../api/client';
import { vibrateLight } from '../utils/vibration';
import SelectedDayPanel from './SelectedDayPanel';

const DAYS_HEADER = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

// Helper for adaptive animation duration
const getAnimationDuration = (base: number) => {
  if (typeof window !== 'undefined' && (window as any).__LOW_PERFORMANCE__) {
    return base * 0.67; // 33% faster on low performance devices
  }
  return base;
};

function getMonthDays(month: Date): Date[] {
  const start = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
  const end = endOfWeek(endOfMonth(month), { weekStartsOn: 1 });
  return eachDayOfInterval({ start, end });
}

// ─── Mapping functions for calendar ──────────────────────────────────
function getSlotsForDate(date: Date, workDays: Record<string, AdminWorkDay>): string[] {
  const formattedDate = format(date, 'yyyy-MM-dd');
  const workDay = workDays[formattedDate];
  return workDay ? workDay.slots.map(s => s.time) : [];
}

function getClientsForDate(date: Date, workDays: Record<string, AdminWorkDay>): Array<{time: string, status: string}> {
  const formattedDate = format(date, 'yyyy-MM-dd');
  const workDay = workDays[formattedDate];
  console.log('getClientsForDate date:', formattedDate, 'workDay:', workDay);
  if (!workDay) return [];
  const clients = workDay.slots
    .filter(s => s.is_booked && s.booking)
    .map(s => ({
      time: s.time,
      status: s.booking!.status
    }));
  console.log('clients for date:', clients);
  return clients;
}

// ─── Nav Button ───────────────────────────────────────────────────────────────
function NavButton({ onClick, direction }: { onClick: () => void; direction: 'left' | 'right' }) {
  return (
    <motion.button
      whileTap={{ scale: 0.90 }}
      onClick={onClick}
      className="liquid-glass-nav w-11 h-11 flex items-center justify-center rounded-2xl
        text-[#a07060] hover:text-[#7c5340] transition-colors duration-200"
    >
      {direction === 'left'
        ? <ChevronLeft size={18} strokeWidth={2.5} />
        : <ChevronRight size={18} strokeWidth={2.5} />
      }
    </motion.button>
  );
}

// ─── Admin DayCard ────────────────────────────────────────────────────────────
interface AdminDayCardProps {
  date: Date;
  slots: string[];
  isCurrentMonth: boolean;
  isSelected: boolean;
  onClick: () => void;
  bookedClients?: Array<{ time: string; status?: string }>;
}

function AdminDayCard({ date, slots, isCurrentMonth, isSelected, onClick, bookedClients = [] }: AdminDayCardProps) {
  const isPast = isBefore(startOfDay(date), startOfDay(new Date()));
  const isToday_ = isToday(date);
  const hasSlots = slots.length > 0;

  const handleClick = () => {
    vibrateLight();
    onClick();
  };

  if (!isCurrentMonth) return <div className="min-h-[64px] rounded-3xl" />;

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.94 }}
      onClick={handleClick}
      className={`
        relative rounded-3xl p-2 min-h-[64px] w-full text-left
        liquid-glass-calendar transition-all duration-200
        ${isPast ? 'opacity-40' : ''}
        ${isSelected ? 'ring-4 ring-[#c4967a] bg-gradient-to-br from-[#f7d5bc]/70 to-[#e8c4a8]/70 shadow-xl shadow-[#c4967a]/30 border-2 border-[#c4967a]/60' : ''}
        ${isToday_ && !isSelected ? 'ring-1 ring-[#2e7d5e]/40' : ''}
      `}
    >
      {/* Day number */}
      <span className={`
        absolute top-2 left-2 z-20 text-[11px] font-semibold leading-none
        ${isToday_ ? 'text-[#2e7d5e]' : 'text-[#3d2b1f]'}
      `}>
        {format(date, 'd')}
      </span>

      {/* Slot dots */}
      {hasSlots && !isPast && (
        <div className="relative z-20 flex flex-wrap gap-0.5 mt-4">
          {slots.map((slot) => {
            const client = bookedClients.find(c => c.time === slot);
            const isBooked = !!client;
            const status = client?.status;

            return (
              <span
                key={slot}
                className={`
                  w-1.5 h-1.5 rounded-full inline-block
                  ${!isBooked
                    ? 'bg-[#a07060]/60'
                    : status === 'pending'
                      ? 'bg-[#ef4444]'
                      : 'bg-[#2e7d5e]'
                  }
                `}
              />
            );
          })}
        </div>
      )}
    </motion.button>
  );
}


export default function AdminSchedulePanel() {
  const [workDays, setWorkDays] = useState<Record<string, AdminWorkDay>>({});
  const [activeTab, setActiveTab] = useState<'calendar' | 'clients'>('calendar');

  // Archive state
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveData, setArchiveData] = useState<UserBooking[]>([]);

  // Calendar navigation state
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await apiClient.getWorkDaysWithBookings();
      setWorkDays(data);
    } catch {
      console.error('Failed to load admin data');
    }
  }, []);

  const loadArchive = useCallback(async () => {
    try {
      const data = await apiClient.getArchive();
      setArchiveData(data);
    } catch {
      console.error('Failed to load archive data');
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(), 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Swipe handlers for calendar navigation
  const swipeHandlers = useSwipeable({
    onSwipedLeft: goToNextMonth,
    onSwipedRight: goToPrevMonth,
    trackTouch: true,
    delta: 50,
  });

  // Calendar navigation functions
  function goToPrevMonth() {
    vibrateLight();
    setCurrentMonth(prev => {
      const newDate = new Date(prev);
      newDate.setMonth(newDate.getMonth() - 1);
      return newDate;
    });
  }

  function goToNextMonth() {
    vibrateLight();
    setCurrentMonth(prev => {
      const newDate = new Date(prev);
      newDate.setMonth(newDate.getMonth() + 1);
      return newDate;
    });
  }

  function selectDate(date: Date) {
    vibrateLight();
    setSelectedDate(date);
  }

  // Calculate calendar data
  const days = getMonthDays(currentMonth);
  const selectedDateKey = selectedDate ? format(selectedDate, 'yyyy-MM-dd') : null;

  return (
    <div className="space-y-4">
      {/* ── Tab Switcher ── */}
      <div className="liquid-glass rounded-2xl p-1.5 flex gap-1.5">
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={() => setActiveTab('calendar')}
          className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors ${
            activeTab === 'calendar'
              ? 'btn-primary'
              : 'liquid-glass-nav text-[#7c5340]'
          }`}
        >
          Календарь
        </motion.button>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={() => setActiveTab('clients')}
          className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors ${
            activeTab === 'clients'
              ? 'btn-primary'
              : 'liquid-glass-nav text-[#7c5340]'
          }`}
        >
          Записи
        </motion.button>
      </div>

      {/* ── Calendar Tab ── */}
      {activeTab === 'calendar' && (
        <AnimatePresence mode="wait">
          <motion.div
            key="calendar"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: getAnimationDuration(0.15) }}
          >
      {/* ── Calendar Grid ── */}
      <div className="liquid-glass-calendar p-3 rounded-2xl" {...swipeHandlers}>
        {/* Month navigation */}
        <div className="flex items-center justify-between mb-3">
          <NavButton direction="left" onClick={goToPrevMonth} />
          <motion.span
            key={format(currentMonth, 'yyyy-MM')}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-[#3d2b1f] font-semibold text-sm capitalize"
          >
            {format(currentMonth, 'LLLL yyyy', { locale: ru })}
          </motion.span>
          <NavButton direction="right" onClick={goToNextMonth} />
        </div>

        {/* Days of week */}
        <div className="grid grid-cols-7 mb-1.5">
          {DAYS_HEADER.map((d) => (
            <div key={d} className="flex items-center justify-center">
              <span className="text-[10px] font-semibold text-[#9e8476] uppercase tracking-widest">
                {d}
              </span>
            </div>
          ))}
        </div>

        {/* Days grid */}
        <div className="grid grid-cols-7 gap-1">
          {days.map((date) => {
            const key = format(date, 'yyyy-MM-dd');
            const slots = getSlotsForDate(date, workDays);
            const clientsForDate = getClientsForDate(date, workDays);

            return (
              <AdminDayCard
                key={key}
                date={date}
                slots={slots}
                isCurrentMonth={isSameMonth(date, currentMonth)}
                isSelected={selectedDateKey === key}
                onClick={() => selectDate(date)}
                bookedClients={clientsForDate}
              />
            );
          })}
        </div>
      </div>

      {/* ── Selected Day Panel ── */}
      <div className="mt-4">
      <AnimatePresence>
        {selectedDate && (
          <SelectedDayPanel
            date={selectedDate}
            workDay={workDays[format(selectedDate, 'yyyy-MM-dd')] || null}
            onAddSlot={async (time) => {
              const dateStr = format(selectedDate, 'yyyy-MM-dd');
              return await apiClient.addTimeSlot(dateStr, time);
            }}
            onCreateWorkDay={async (dateStr) => {
              return await apiClient.addWorkDay(dateStr);
            }}
            onDeleteSlot={async (time) => {
              const dateStr = format(selectedDate, 'yyyy-MM-dd');
              return await apiClient.deleteTimeSlot(dateStr, time);
            }}
            onUpdateClient={async (data) => {
              return await apiClient.updateClient(data);
            }}
            onDeleteClient={async (time) => {
              const dateStr = format(selectedDate, 'yyyy-MM-dd');
              return await apiClient.deleteClient(dateStr, time);
            }}
            onRefresh={() => loadData()}
          />
        )}
      </AnimatePresence>
      </div>
          </motion.div>
        </AnimatePresence>
      )}

      {/* ── Bookings Tab ── */}
      {activeTab === 'clients' && (
        <AnimatePresence mode="wait">
          <motion.div
            key="clients"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: getAnimationDuration(0.15) }}
            className="space-y-4"
          >
            {/* Active bookings */}
            <div className="liquid-glass rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-[#3d2b1f] mb-3">Активные записи</h3>
              {Object.values(workDays).flatMap(day =>
                day.slots.filter(s => s.is_booked && s.booking && ['pending', 'confirmed'].includes(s.booking.status))
                  .map(s => ({
                    date: day.day_date,
                    time: s.time,
                    booking: s.booking!
                  }))
              ).length === 0 ? (
                <p className="text-xs text-[#9e8476]">Нет активных записей</p>
              ) : (
                <div className="space-y-2">
                  {Object.values(workDays).flatMap(day =>
                    day.slots.filter(s => s.is_booked && s.booking && ['pending', 'confirmed'].includes(s.booking.status))
                      .map(s => ({
                        date: day.day_date,
                        time: s.time,
                        booking: s.booking!
                      }))
                  ).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).map((booking) => (
                    <div key={`${booking.date}-${booking.time}`} className="p-3 bg-white/30 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium text-[#3d2b1f]">{booking.booking.client_name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          booking.booking.status === 'confirmed'
                            ? 'badge-confirmed'
                            : 'badge-pending'
                        }`}>
                          {booking.booking.status === 'confirmed' ? 'Подтверждена' : 'Ожидает'}
                        </span>
                      </div>
                      <p className="text-xs text-[#9e8476]">{booking.date} в {booking.time}</p>
                      {booking.booking.phone && <p className="text-xs text-[#9e8476] mt-1">{booking.booking.phone}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Pending confirmations */}
            {Object.values(workDays).flatMap(day =>
              day.slots.filter(s => s.is_booked && s.booking && s.booking.status === 'pending')
            ).length > 0 && (
              <div className="liquid-glass rounded-2xl p-4">
                <h3 className="text-sm font-semibold text-[#3d2b1f] mb-3">Требующие подтверждения</h3>
                <div className="space-y-2">
                  {Object.values(workDays).flatMap(day =>
                    day.slots.filter(s => s.is_booked && s.booking && s.booking.status === 'pending')
                      .map(s => ({
                        date: day.day_date,
                        time: s.time,
                        booking: s.booking!
                      }))
                  ).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()).map((booking) => (
                    <div key={`${booking.date}-${booking.time}`} className="flex items-center justify-between p-3 bg-white/30 rounded-xl">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[#3d2b1f]">{booking.booking.client_name}</p>
                        <p className="text-xs text-[#9e8476]">{booking.date} в {booking.time}</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            const result = await apiClient.updateClient({
                              name: booking.booking.client_name,
                              phone: booking.booking.phone,
                              date: booking.date,
                              time: booking.time,
                              username: booking.booking.username,
                              note: booking.booking.note,
                              status: 'confirmed'
                            });
                            if (result.success) {
                              loadData();
                            }
                          }}
                          className="px-3 py-1.5 rounded-lg bg-[#2e7d5e] text-white text-xs font-medium hover:scale-105 active:scale-95 transition-all duration-200"
                        >
                          Подтвердить
                        </button>
                        <button
                          onClick={async () => {
                            const result = await apiClient.deleteClient(booking.date, booking.time);
                            if (result.success) {
                              loadData();
                            }
                          }}
                          className="px-3 py-1.5 rounded-lg bg-[#ef4444] text-white text-xs font-medium hover:scale-105 active:scale-95 transition-all duration-200"
                        >
                          Отклонить
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Archive button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={async () => {
                setArchiveOpen(true);
                await loadArchive();
              }}
              className="w-full liquid-glass rounded-2xl p-4 text-left"
            >
              <div className="flex items-center gap-3">
                <div className="text-2xl">📁</div>
                <div>
                  <h3 className="text-sm font-semibold text-[#3d2b1f]">Архив записей</h3>
                  <p className="text-xs text-[#9e8476] mt-0.5">Завершенные и отмененные записи</p>
                </div>
              </div>
            </motion.button>
          </motion.div>
        </AnimatePresence>
      )}

      {/* ── Archive Modal ── */}
      <AnimatePresence>
        {archiveOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setArchiveOpen(false)}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: getAnimationDuration(0.15) }}
              onClick={(e) => e.stopPropagation()}
              className="liquid-glass rounded-2xl p-4 max-w-md w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-[#3d2b1f]">📁 Архив записей</h3>
                <button
                  onClick={() => setArchiveOpen(false)}
                  className="text-[#9e8476] hover:text-[#3d2b1f] transition-colors"
                >
                  ✕
                </button>
              </div>

              {archiveData.length === 0 ? (
                <p className="text-xs text-[#9e8476] text-center py-8">Архив пуст</p>
              ) : (
                <div className="space-y-3">
                  {archiveData.map((booking) => (
                    <div
                      key={booking.id}
                      className="p-3 bg-white/30 rounded-xl"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium text-[#3d2b1f]">{booking.client_name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          booking.status === 'completed'
                            ? 'bg-[#2e7d5e]/20 text-[#2e7d5e]'
                            : 'bg-[#ef4444]/20 text-[#ef4444]'
                        }`}>
                          {booking.status === 'completed' ? 'Завершена' : 'Отменена'}
                        </span>
                      </div>
                      <p className="text-xs text-[#9e8476]">{booking.day_date} в {booking.slot_time}</p>
                      {booking.phone && <p className="text-xs text-[#9e8476] mt-1">{booking.phone}</p>}
                      {booking.cancel_reason && (
                        <p className="text-xs text-[#ef4444] mt-1">Причина: {booking.cancel_reason}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
