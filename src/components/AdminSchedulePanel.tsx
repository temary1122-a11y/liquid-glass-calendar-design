// ============================================================
// src/components/AdminSchedulePanel.tsx — Панель управления для мастера
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { format, isSameMonth, isToday, startOfMonth, endOfMonth, eachDayOfInterval, startOfWeek, endOfWeek, isBefore, startOfDay } from 'date-fns';
import { ru } from 'date-fns/locale';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSwipeable } from 'react-swipeable';
import { apiClient, type AdminWorkDay } from '../api/client';
import { vibrateLight } from '../utils/vibration';
import SelectedDayPanel from './SelectedDayPanel';

const DAYS_HEADER = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

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
        ${isSelected ? 'ring-2 ring-[#7c5340]/50 bg-white/20' : ''}
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
          Клиенты
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
            transition={{ duration: 0.2 }}
          >
      {/* ── Calendar Grid ── */}
      <div className="liquid-glass-calendar p-3" {...swipeHandlers}>
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
          </motion.div>
        </AnimatePresence>
      )}

      {/* ── Clients Tab ── */}
      {activeTab === 'clients' && (
        <AnimatePresence mode="wait">
          <motion.div
            key="clients"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="space-y-4"
          >
            {/* Stats bar */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'Рабочих дней', value: Object.keys(workDays).length },
                { label: 'Всего слотов', value: Object.values(workDays).reduce((s, d) => s + d.slots.length, 0) },
                { label: 'Записей', value: Object.values(workDays).reduce((s, d) => s + d.slots.filter((sl) => sl.is_booked && sl.booking?.status === 'pending').length, 0) },
              ].map((stat) => (
                <div key={stat.label} className="liquid-glass rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-[#3d2b1f]">{stat.value}</p>
                  <p className="text-[10px] text-[#9e8476] mt-0.5">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Bookings history */}
            <div className="liquid-glass rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-[#3d2b1f] mb-3">История записей</h3>
              <p className="text-xs text-[#9e8476]">Скоро будет добавлено...</p>
            </div>

            {/* Pending confirmations */}
            <div className="liquid-glass rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-[#3d2b1f] mb-3">Требующие подтверждения</h3>
              {Object.values(workDays).flatMap(day =>
                day.slots.filter(s => s.is_booked && s.booking && s.booking.status === 'pending')
                  .map(s => ({
                    date: day.day_date,
                    time: s.time,
                    client: s.booking!
                  }))
              ).length === 0 ? (
                <p className="text-xs text-[#9e8476]">Нет записей требующих подтверждения</p>
              ) : (
                <div className="space-y-2">
                  {Object.values(workDays).flatMap(day =>
                    day.slots.filter(s => s.is_booked && s.booking && s.booking.status === 'pending')
                      .map(s => ({
                        date: day.day_date,
                        time: s.time,
                        client: s.booking!
                      }))
                  ).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).map((booking) => (
                    <div key={`${booking.date}-${booking.time}`} className="flex items-center justify-between p-3 bg-white/30 rounded-xl">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[#3d2b1f]">{booking.client.client_name}</p>
                        <p className="text-xs text-[#9e8476]">{booking.date} в {booking.time}</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onMouseDown={() => console.log('Confirm button onMouseDown')}
                          onClick={async (e) => {
                            console.log('Confirm button onClick triggered');
                            e.stopPropagation();
                            console.log('Confirm button clicked for:', booking);
                            const result = await apiClient.updateClient({
                              name: booking.client.client_name,
                              phone: booking.client.phone,
                              date: booking.date,
                              time: booking.time,
                              username: booking.client.username,
                              note: booking.client.note,
                              status: 'confirmed'
                            });
                            console.log('Confirm result:', result);
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
                            console.log('Reject button clicked for:', booking);
                            const result = await apiClient.deleteClient(booking.date, booking.time);
                            console.log('Reject result:', result);
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
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
