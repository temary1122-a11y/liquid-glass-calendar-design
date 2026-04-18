// ============================================================
// src/components/TimePicker.tsx — Simple Time Picker
// ============================================================

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface TimePickerProps {
  value: string;
  onChange: (time: string) => void;
  onClose: () => void;
}

export default function TimePicker({ value, onChange, onClose }: TimePickerProps) {
  const [time, setTime] = useState(value);

  useEffect(() => {
    setTime(value);
  }, [value]);

  const handleVibrate = () => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.HapticFeedback) {
      try {
        tg.HapticFeedback.selectionChanged();
      } catch (error) {
        console.warn('Haptic feedback error:', error);
      }
    }
  };

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleVibrate();
    setTime(e.target.value);
    onChange(e.target.value);
  };

  const handleConfirm = () => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.HapticFeedback) {
      try {
        tg.HapticFeedback.notificationOccurred('success');
      } catch (error) {
        console.warn('Haptic feedback error:', error);
      }
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
      <motion.div
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        className="w-full max-w-lg bg-white/95 backdrop-blur-xl rounded-t-3xl p-6 border-t border-white/30"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={onClose}
            className="text-[#c4967a] text-sm font-semibold"
          >
            Отмена
          </button>
          <h3 className="text-[#3d2b1f] text-base font-semibold">Выберите время</h3>
          <button
            onClick={handleConfirm}
            className="text-[#2e7d5e] text-sm font-semibold"
          >
            Готово
          </button>
        </div>

        {/* Time Input */}
        <div className="flex items-center justify-center">
          <input
            type="time"
            value={time}
            onChange={handleTimeChange}
            className="
              w-48 h-14 text-2xl text-[#3d2b1f] font-semibold
              bg-[#f7d5bc]/30 border-2 border-[#c4967a]/30 rounded-2xl
              text-center focus:outline-none focus:border-[#c4967a]
              transition-all duration-200
            "
            step={900} // 15 minutes
          />
        </div>

        {/* Quick select buttons */}
        <div className="grid grid-cols-4 gap-3 mt-6">
          {['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'].map((quickTime) => (
            <motion.button
              key={quickTime}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                handleVibrate();
                setTime(quickTime);
                onChange(quickTime);
              }}
              className={`
                h-12 text-sm font-medium rounded-xl
                transition-all duration-200
                ${time === quickTime
                  ? 'bg-[#c4967a] text-white shadow-lg'
                  : 'bg-[#f7d5bc]/30 text-[#3d2b1f] hover:bg-[#f7d5bc]/50'
                }
              `}
            >
              {quickTime}
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
