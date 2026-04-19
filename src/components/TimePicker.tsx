// ============================================================
// src/components/TimePicker.tsx — iOS-style Time Picker
// ============================================================

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TimePickerRoot,
  TimePickerWheels,
  TimePickerWheel,
  TimePickerSeparator,
  TimePickerButton,
} from '@poursha98/react-ios-time-picker';
import { useVibration, VIBRATION_PATTERNS } from '../hooks/useVibration';

interface TimePickerProps {
  value: string;
  onChange: (time: string) => void;
  onConfirm?: () => void;
  onClose: () => void;
  open: boolean;
  title?: string;
}

export default function TimePicker({
  value,
  onChange,
  onConfirm,
  onClose,
  open,
  title = 'Выберите время',
}: TimePickerProps) {
  const { vibrate } = useVibration();

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

  const handleConfirm = () => {
    vibrate(VIBRATION_PATTERNS.SUCCESS);
    if (onConfirm) {
      onConfirm();
    }
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
            onClick={onClose}
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
            <div className="w-full max-w-lg bg-white/95 backdrop-blur-xl rounded-t-3xl p-6 border-t border-white/30">
              {/* TimePicker using compound components */}
              <TimePickerRoot
                value={value}
                onChange={onChange}
                onConfirm={handleConfirm}
                minutes={[0, 15, 30, 45]}
                className="!bg-transparent !rounded-none !px-0 !pt-0 !pb-0"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-6 px-0">
                  <button
                    onClick={onClose}
                    className="text-[#c4967a] text-sm font-semibold"
                  >
                    Отмена
                  </button>
                  <h3 className="text-[#3d2b1f] text-base font-semibold">{title}</h3>
                  {/* TimePickerButton will be used instead */}
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

                <TimePickerButton className="!w-full !mt-6 !py-3 !px-6 !rounded-xl !text-white !font-semibold !text-sm !border-none !cursor-pointer !shadow-lg bg-gradient-to-r from-[#c4967a] to-[#b07d62]">
                  Готово
                </TimePickerButton>
              </TimePickerRoot>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
