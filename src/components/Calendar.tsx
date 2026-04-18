import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { createPortal } from 'react-dom';
import BookingForm from './BookingForm';
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isToday,
  isBefore,
  startOfDay,
} from 'date-fns';
import { ru } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';
import { useSwipeable } from 'react-swipeable';

// ─── Mock data ────────────────────────────────────────────────────────────────
// Тестовые данные удалены - слоты загружаются из API
const MOCK_SLOTS: Record<string, string[]> = {};

const DAYS_HEADER = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const VISIBLE_SLOTS = 3; // slots shown before overflow

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getMonthDays(month: Date): Date[] {
  const start = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
  const end = endOfWeek(endOfMonth(month), { weekStartsOn: 1 });
  return eachDayOfInterval({ start, end });
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface NavButtonProps {
  onClick: () => void;
  direction: 'left' | 'right';
}

function NavButton({ onClick, direction }: NavButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.90 }}
      onClick={onClick}
      className="liquid-glass-nav w-11 h-11 flex items-center justify-center rounded-2xl
        text-[#a07060] hover:text-[#7c5340] transition-colors duration-200"
      aria-label={direction === 'left' ? 'Предыдущий месяц' : 'Следующий месяц'}
    >
      {direction === 'left'
        ? <ChevronLeft size={18} strokeWidth={2.5} />
        : <ChevronRight size={18} strokeWidth={2.5} />
      }
    </motion.button>
  );
}

interface SlotButtonProps {
  time: string;
  onClick?: () => void;
}

function SlotButton({ time, onClick }: SlotButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.94 }}
      onClick={onClick}
      className="liquid-glass-slot h-5.5 w-full px-1 rounded-lg
        flex items-center justify-center
        text-[#8b6049] text-[10px] font-semibold tracking-wide
        hover:shadow-[0_6px_20px_rgba(0,0,0,0.10)]
        transition-all duration-200 select-none"
    >
      {time}
    </motion.button>
  );
}

interface GhostExpandButtonProps {
  count: number;
  onClick: () => void;
}

function GhostExpandButton({ count, onClick }: GhostExpandButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="absolute bottom-[-5px] left-1 right-1 h-4.5 flex items-center justify-center gap-0.5
        rounded-lg bg-white/5 hover:bg-white/12
        text-[#c4967a] text-[9px] font-medium
        transition-all duration-200 select-none"
    >
      <span>+{count}</span>
      <ChevronDown size={9} strokeWidth={2.5} />
    </motion.button>
  );
}

interface CollapseButtonProps {
  onClick: () => void;
}

function CollapseButton({ onClick }: CollapseButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="absolute bottom-0 left-1 right-1 h-3.5 flex items-center justify-center
        text-[#c4967a] hover:text-[#a07060]
        transition-colors duration-200 select-none"
    >
      <ChevronUp size={9} strokeWidth={2.5} />
    </motion.button>
  );
}

// ─── DayCard ─────────────────────────────────────────────────────────────────

interface DayCardProps {
  date: Date;
  slots: string[];
  isCurrentMonth: boolean;
  isExpanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onSlotClick: (time: string) => void;
}

function DayCard({
  date,
  slots,
  isCurrentMonth,
  isExpanded,
  onExpand,
  onCollapse,
  onSlotClick,
}: DayCardProps) {
  const isPast = isBefore(startOfDay(date), startOfDay(new Date()));
  const isCurrentDay = isToday(date);
  const dateKey = format(date, 'yyyy-MM-dd');
  const hasSlots = slots.length > 0;
  const visibleSlots = slots.slice(0, VISIBLE_SLOTS);
  const hiddenSlots = slots.slice(VISIBLE_SLOTS);
  const overflowCount = hiddenSlots.length;

  if (!isCurrentMonth) {
    return (
      <div className="rounded-3xl min-h-[90px]" />
    );
  }

  return (
    <motion.div
      layout
      layoutId={dateKey}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className={`
        relative rounded-3xl p-1 pb-0.5 min-h-[90px]
        liquid-glass-calendar cursor-default select-none
        ${isPast ? 'opacity-45' : ''}
        ${isCurrentDay ? 'ring-1 ring-[#2e7d5e]/40' : ''}
      `}
    >
      {/* Glass highlight shimmer */}
      <div className="glass-highlight absolute inset-x-0 top-0 h-[45%] rounded-t-3xl pointer-events-none z-10" />

      {/* Day number */}
      <div className="absolute top-[-8px] left-[-3px] z-20">
        <span className={`
          text-[11px] font-semibold tracking-tight leading-none
          ${isCurrentDay ? 'text-[#2e7d5e]' : 'text-[#3d2b1f]'}
        `}>
          {format(date, 'd')}
        </span>
      </div>

      {/* Visible slots */}
      {hasSlots && !isPast && (
        <motion.div layout className="flex flex-col gap-0 pt-2">
          {visibleSlots.map(time => (
            <SlotButton
              key={time}
              time={time}
              onClick={() => onSlotClick?.(time)}
            />
          ))}

          {/* Expanded hidden slots */}
          <AnimatePresence initial={false}>
            {isExpanded && (
              <motion.div
                key="expanded"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{
                  height:  { duration: 0.30, ease: [0.16, 1, 0.3, 1] },
                  opacity: { duration: 0.20, ease: 'easeOut' },
                }}
                className="flex flex-col gap-0"
              >
                {hiddenSlots.map(time => (
                  <SlotButton
                    key={time}
                    time={time}
                    onClick={() => onSlotClick?.(time)}
                  />
                ))}
                <CollapseButton onClick={onCollapse} />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Ghost expand button - absolutely positioned at bottom */}
      {hasSlots && !isPast && overflowCount > 0 && !isExpanded && (
        <GhostExpandButton count={overflowCount} onClick={onExpand} />
      )}

      {/* No slots placeholder */}
      {(!hasSlots || isPast) && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[10px] text-[#9e8476]/50">—</span>
        </div>
      )}
    </motion.div>
  );
}

// ─── Main Calendar ────────────────────────────────────────────────────────────

export default function Calendar() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [expandedWeek, setExpandedWeek] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<{ date: Date; time: string; availableSlots: string[] } | null>(null);
  const [bookingFormOpen, setBookingFormOpen] = useState(false);

  const days = getMonthDays(currentMonth);

  const prevMonth = useCallback(() => {
    setCurrentMonth(m => new Date(m.getFullYear(), m.getMonth() - 1, 1));
    setExpandedWeek(false);
  }, []);

  const nextMonth = useCallback(() => {
    setCurrentMonth(m => new Date(m.getFullYear(), m.getMonth() + 1, 1));
    setExpandedWeek(false);
  }, []);

  const swipeHandlers = useSwipeable({
    onSwipedLeft:  nextMonth,
    onSwipedRight: prevMonth,
    trackMouse: false,
    trackTouch: true,
    delta: 50,
  });

  return (
    <div className="liquid-glass-calendar p-4 w-full" {...swipeHandlers}>
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-4">
        <NavButton direction="left" onClick={prevMonth} />

        <motion.span
          key={format(currentMonth, 'yyyy-MM')}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.20 }}
          className="text-[#3d2b1f] font-semibold text-sm capitalize"
        >
          {format(currentMonth, 'LLLL yyyy', { locale: ru })}
        </motion.span>

        <NavButton direction="right" onClick={nextMonth} />
      </div>

      {/* ── Days-of-week header ── */}
      <div className="grid grid-cols-7 mb-2">
        {DAYS_HEADER.map(day => (
          <div key={day} className="flex items-center justify-center">
            <span className="text-[10px] font-semibold text-[#9e8476] uppercase tracking-widest">
              {day}
            </span>
          </div>
        ))}
      </div>

      {/* ── Days grid ── */}
      <motion.div layout className="grid grid-cols-7 gap-1.5">
        {days.map(date => {
          const key = format(date, 'yyyy-MM-dd');
          const slots = MOCK_SLOTS[key] ?? [];
          return (
            <DayCard
              key={key}
              date={date}
              slots={slots}
              isCurrentMonth={isSameMonth(date, currentMonth)}
              isExpanded={expandedWeek}
              onExpand={() => setExpandedWeek(true)}
              onCollapse={() => setExpandedWeek(false)}
              onSlotClick={time => {
                setSelectedSlot({ date, time, availableSlots: slots });
                setBookingFormOpen(true);
              }}
            />
          );
        })}
      </motion.div>

      {/* Booking Form Modal - рендерится в document.body через Portal */}
      {bookingFormOpen && selectedSlot &&
        createPortal(
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-md p-4"
            onClick={() => setBookingFormOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <BookingForm
                date={selectedSlot.date}
                time={selectedSlot.time}
                availableSlots={selectedSlot.availableSlots}
                onTimeChange={(newTime) => setSelectedSlot({ ...selectedSlot, time: newTime })}
                onClose={() => setBookingFormOpen(false)}
              />
            </motion.div>
          </motion.div>,
          document.body
        )
      }
    </div>
  );
}
