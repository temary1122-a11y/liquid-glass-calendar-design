// ============================================================
// src/components/Calendar.tsx — Календарь выбора даты и слота
// ============================================================

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { apiClient, type WorkDay } from '../api/client';
import BookingForm from './BookingForm';
import { vibrateLight, vibrateSelection, vibrateMedium } from '../utils/vibration';

const MONTH_NAMES = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];

const DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

interface CalendarProps {
  hasActiveBooking?: boolean;
  onBookingCreated?: () => void;
}

export default function Calendar({ hasActiveBooking = false, onBookingCreated }: CalendarProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [workDays, setWorkDays] = useState<WorkDay[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showBookingForm, setShowBookingForm] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const calendarRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLDivElement>(null);

  // Map: "YYYY-MM-DD" → slots[]
  const availableDatesMap = workDays.reduce<Record<string, string[]>>((acc, wd) => {
    acc[wd.date] = wd.slots.filter((s) => s.available).map((s) => s.time);
    return acc;
  }, {});

  const loadDates = useCallback(async (quiet = false) => {
    if (!quiet) setIsLoading(true);
    else setIsRefreshing(true);
    try {
      const data = await apiClient.getAvailableDates();
      setWorkDays(data);
    } catch {
      console.error('Failed to load dates');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDates();
  }, [loadDates]);

  // Calendar grid helpers
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
  // Convert Sunday=0 → 6, Monday=1 → 0, etc.
  const startOffset = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1;

  function toDateKey(year: number, month: number, day: number): string {
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  function toDate(year: number, month: number, day: number): Date {
    const d = new Date(year, month, day);
    d.setHours(0, 0, 0, 0);
    return d;
  }

  function prevMonth() {
    vibrateLight();
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
    setSelectedDate(null);
    setSelectedTime(null);
    setShowBookingForm(false);
  }

  function nextMonth() {
    vibrateLight();
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
    setSelectedDate(null);
    setSelectedTime(null);
    setShowBookingForm(false);
  }

  function handleDayClick(day: number) {
    const date = toDate(currentYear, currentMonth, day);
    const key = toDateKey(currentYear, currentMonth, day);
    const isAvailable = !!availableDatesMap[key]?.length;
    const isPast = date < today;

    if (isPast || !isAvailable) return;

    vibrateSelection();
    setSelectedDate(date);
    setSelectedTime(null);
    setShowBookingForm(false);

    // Scroll to slots
    setTimeout(() => {
      calendarRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }

  function handleSlotClick(time: string) {
    if (hasActiveBooking) {
      alert('Вы уже записаны! Отмените текущую запись, чтобы записаться заново.');
      return;
    }
    vibrateMedium();
    setSelectedTime(time);
    setShowBookingForm(true);
    setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }

  function handleBookingClose() {
    setShowBookingForm(false);
    setSelectedDate(null);
    setSelectedTime(null);
    loadDates(true);
    onBookingCreated?.();
  }

  const selectedDateKey = selectedDate
    ? toDateKey(
        selectedDate.getFullYear(),
        selectedDate.getMonth(),
        selectedDate.getDate()
      )
    : null;

  const slotsForSelected = selectedDateKey ? (availableDatesMap[selectedDateKey] || []) : [];

  return (
    <div ref={calendarRef} className="space-y-3">
      {/* ── Calendar Card ── */}
      <div className="liquid-glass rounded-2xl p-4">
        {/* Month navigation */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={prevMonth}
            className="w-9 h-9 flex items-center justify-center rounded-xl liquid-glass-nav
              text-[#9e8476] hover:text-[#7c5340] transition-colors active:scale-90"
          >
            <ChevronLeft size={18} />
          </button>

          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#3d2b1f]">
              {MONTH_NAMES[currentMonth]} {currentYear}
            </h2>
            {isRefreshing && (
              <div className="w-3.5 h-3.5 border-2 border-[#c4967a]/30 border-t-[#c4967a] rounded-full spinner" />
            )}
          </div>

          <button
            onClick={nextMonth}
            className="w-9 h-9 flex items-center justify-center rounded-xl liquid-glass-nav
              text-[#9e8476] hover:text-[#7c5340] transition-colors active:scale-90"
          >
            <ChevronRight size={18} />
          </button>
        </div>

        {/* Day headers */}
        <div className="grid grid-cols-7 mb-2">
          {DAY_NAMES.map((d) => (
            <div key={d} className="text-center text-[10px] font-medium text-[#9e8476] py-1">
              {d}
            </div>
          ))}
        </div>

        {/* Day cells */}
        {isLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-[#c4967a]/30 border-t-[#c4967a] rounded-full spinner mx-auto mb-2" />
              <p className="text-xs text-[#9e8476]">Загрузка...</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-0.5">
            {/* Empty cells for offset */}
            {Array.from({ length: startOffset }).map((_, i) => (
              <div key={`empty-${i}`} />
            ))}

            {/* Day cells */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const date = toDate(currentYear, currentMonth, day);
              const key = toDateKey(currentYear, currentMonth, day);
              const isPast = date < today;
              const isToday = date.getTime() === today.getTime();
              const hasSlots = !!availableDatesMap[key]?.length;
              const isSelected =
                selectedDate?.getTime() === date.getTime();

              let cellClass = 'day-cell w-full aspect-square flex flex-col items-center justify-center text-sm rounded-xl ';

              if (isSelected) {
                cellClass += 'selected ';
              } else if (isPast) {
                cellClass += 'disabled ';
              } else if (!hasSlots) {
                cellClass += 'disabled ';
              } else {
                cellClass += 'available ';
                if (isToday) cellClass += 'today ';
              }

              return (
                <motion.button
                  key={day}
                  whileTap={!isPast && hasSlots ? { scale: 0.88 } : {}}
                  onClick={() => handleDayClick(day)}
                  disabled={isPast || !hasSlots}
                  className={cellClass}
                >
                  <span className="text-sm leading-none">{day}</span>
                  {hasSlots && !isSelected && !isPast && (
                    <span className="w-1 h-1 rounded-full bg-[#c4967a] mt-0.5 pulse-dot" />
                  )}
                </motion.button>
              );
            })}
          </div>
        )}

        {/* Legend */}
        <div className="mt-3 flex items-center gap-4 justify-center">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#c4967a]" />
            <span className="text-[10px] text-[#9e8476]">Доступные дни</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-4 rounded-md bg-gradient-to-br from-[#c4967a] to-[#b0856a]" />
            <span className="text-[10px] text-[#9e8476]">Выбранный день</span>
          </div>
        </div>
      </div>

      {/* ── Time Slots ── */}
      <AnimatePresence>
        {selectedDate && (
          <motion.div
            key="slots"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="liquid-glass rounded-2xl p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-[#3d2b1f]">
                {selectedDate.toLocaleDateString('ru-RU', {
                  day: 'numeric',
                  month: 'long',
                })}
              </p>
              <button
                onClick={() => loadDates(true)}
                className="w-7 h-7 flex items-center justify-center rounded-lg liquid-glass-nav
                  text-[#9e8476] transition-colors active:scale-90"
              >
                <RefreshCw size={13} className={isRefreshing ? 'spinner' : ''} />
              </button>
            </div>

            {slotsForSelected.length === 0 ? (
              <p className="text-sm text-[#9e8476] text-center py-3">
                Нет доступных слотов
              </p>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {slotsForSelected.map((time) => (
                  <motion.button
                    key={time}
                    whileTap={{ scale: 0.92 }}
                    onClick={() => handleSlotClick(time)}
                    className={`slot-btn py-2.5 rounded-xl text-sm font-medium ${
                      selectedTime === time ? 'selected' : ''
                    }`}
                  >
                    {time}
                  </motion.button>
                ))}
              </div>
            )}

            {hasActiveBooking && (
              <p className="text-xs text-amber-600 text-center mt-3 bg-amber-50/60 rounded-lg p-2">
                ⚠️ Вы уже записаны. Отмените текущую запись для новой записи.
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Booking Form ── */}
      <AnimatePresence>
        {showBookingForm && selectedDate && selectedTime && (
          <motion.div
            ref={formRef}
            key="booking-form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.30, ease: [0.16, 1, 0.3, 1] }}
          >
            <BookingForm
              date={selectedDate}
              time={selectedTime}
              availableSlots={slotsForSelected}
              onTimeChange={(t) => {
                vibrateSelection();
                setSelectedTime(t);
              }}
              onClose={handleBookingClose}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
