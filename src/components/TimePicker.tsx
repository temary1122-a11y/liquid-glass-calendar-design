// ============================================================
// src/components/TimePicker.tsx — iOS-style Time Picker
// ============================================================

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TimePicker as LibraryTimePicker } from '@poursha98/react-ios-time-picker';
import { useVibration, VIBRATION_PATTERNS } from '../hooks/useVibration';

interface TimePickerProps {
  value: string;
  onChange: (time: string) => void;
  onConfirm?: () => void;
  onClose: () => void;
  open: boolean;
}

export default function TimePicker({
  value,
  onChange,
  onConfirm,
  onClose,
  open,
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
              {/* TimePicker using All-in-One component */}
              <LibraryTimePicker
                value={value}
                onChange={onChange}
                onConfirm={handleConfirm}
                className="!bg-transparent !rounded-none"
              />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
