// ============================================================
// src/components/TimePicker.tsx — iOS-style Time Picker
// ============================================================

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TimePickerRoot,
  TimePickerTitle,
  TimePickerWheels,
  TimePickerWheel,
  TimePickerSeparator,
  TimePickerButton,
} from '@poursha98/react-ios-time-picker';

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
        console.log('Haptic feedback executed');
      } catch (error) {
        console.warn('Haptic feedback error:', error);
      }
    } else {
      console.warn('Haptic feedback not available');
    }
  };

  const handleConfirm = () => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.HapticFeedback) {
      try {
        tg.HapticFeedback.notificationOccurred('success');
        console.log('Haptic success executed');
      } catch (error) {
        console.warn('Haptic feedback error:', error);
      }
    }
    onClose();
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm">
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          className="w-full max-w-lg"
        >
          <TimePickerRoot
            value={time}
            onChange={(newTime) => {
              handleVibrate();
              setTime(newTime);
              onChange(newTime);
            }}
            className="bg-white/95 backdrop-blur-xl rounded-t-3xl p-6 border-t border-white/30"
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
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={handleConfirm}
                className="text-[#2e7d5e] text-sm font-semibold"
              >
                Готово
              </motion.button>
            </div>

            {/* Time Picker Wheels */}
            <TimePickerWheels className="flex justify-center items-center gap-2">
              <TimePickerWheel
                type="hour"
                className="bg-[#f7d5bc]/30 backdrop-blur-sm rounded-lg"
                classNames={{
                  item: 'text-[#9e8476]',
                  selectedItem: 'text-[#3d2b1f] font-semibold',
                }}
              />
              <TimePickerSeparator className="text-[#c4967a] text-3xl font-bold">
                :
              </TimePickerSeparator>
              <TimePickerWheel
                type="minute"
                className="bg-[#f7d5bc]/30 backdrop-blur-sm rounded-lg"
                classNames={{
                  item: 'text-[#9e8476]',
                  selectedItem: 'text-[#3d2b1f] font-semibold',
                }}
              />
            </TimePickerWheels>
          </TimePickerRoot>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
