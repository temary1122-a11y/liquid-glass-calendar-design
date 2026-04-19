// ============================================================
// src/components/TimePicker.tsx — iOS-style Time Picker
// ============================================================

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import RCTimePicker from 'rc-time-picker';
import moment from 'moment';
import 'rc-time-picker/assets/index.css';
import { useVibration, VIBRATION_PATTERNS } from '../hooks/useVibration';
import { Clock } from 'lucide-react';

interface TimePickerProps {
  value: string;
  onChange: (time: string) => void;
  onConfirm?: () => void;
  onClose: () => void;
  open: boolean;
}

// Быстрые пресеты для популярных времен
const TIME_PRESETS = ['09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'];

export default function TimePicker({
  value,
  onChange,
  onConfirm,
  onClose,
  open,
}: TimePickerProps) {
  const { vibrate } = useVibration();
  const [localValue, setLocalValue] = useState<moment.Moment | undefined>(value ? moment(value, 'HH:mm') : undefined);

  // Синхронизируем localValue при открытии
  useEffect(() => {
    if (open) {
      setLocalValue(value ? moment(value, 'HH:mm') : moment().hour(9).minute(0));
    }
  }, [open, value]);

  // Prevent body scroll when picker is open
  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open]);

  const handlePresetClick = (time: string) => {
    vibrate(VIBRATION_PATTERNS.LIGHT);
    setLocalValue(moment(time, 'HH:mm'));
  };

  const handleConfirm = () => {
    if (localValue) {
      const timeString = localValue.format('HH:mm');
      onChange(timeString);
      vibrate(VIBRATION_PATTERNS.SUCCESS);
      if (onConfirm) {
        onConfirm();
      }
    }
    onClose();
  };

  const handleCancel = () => {
    vibrate(VIBRATION_PATTERNS.LIGHT);
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={handleCancel}
          />

          {/* Picker Sheet */}
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-50 flex items-end justify-center"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-full max-w-lg bg-white/95 backdrop-blur-xl rounded-t-3xl border-t border-white/30">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-black/5">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleCancel}
                  className="text-[#9e8476] text-sm font-medium"
                >
                  Отмена
                </motion.button>
                <div className="flex items-center gap-2">
                  <Clock size={16} className="text-[#a07060]" />
                  <span className="text-[#3d2b1f] text-sm font-semibold">Выберите время</span>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleConfirm}
                  className="text-[#2e7d5e] text-sm font-semibold"
                >
                  Готово
                </motion.button>
              </div>

              {/* Quick Presets */}
              <div className="px-6 py-3 border-b border-black/5">
                <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                  {TIME_PRESETS.map((time) => (
                    <motion.button
                      key={time}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handlePresetClick(time)}
                      className={`
                        flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                        ${localValue?.format('HH:mm') === time
                          ? 'bg-[#2e7d5e] text-white shadow-md'
                          : 'bg-[#f5f0e8] text-[#7c5340] hover:bg-[#e8e0d0]'
                        }
                      `}
                    >
                      {time}
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Time Picker */}
              <div className="p-6">
                <RCTimePicker
                  value={localValue}
                  onChange={(value) => {
                    if (value) {
                      setLocalValue(value);
                      vibrate(VIBRATION_PATTERNS.LIGHT);
                    }
                  }}
                  showSecond={false}
                  format="HH:mm"
                  className="w-full"
                  popupClassName="ios-time-picker-popup"
                />
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
