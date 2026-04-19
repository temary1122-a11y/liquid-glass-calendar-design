import { useEffect, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useVibration, VIBRATION_PATTERNS } from "../hooks/useVibration";

export interface TimePickerProps {
  value: string; // "HH:mm"
  onChange: (time: string) => void; // live preview
  onConfirm?: () => void; // commit action in parent (optional)
  onClose: () => void; // close sheet
  open: boolean;
}

const TIME_PRESETS = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"] as const;

export default function TimePicker({ value, onChange, onConfirm, onClose, open }: TimePickerProps) {
  const { vibrate } = useVibration();

  const [localValue, setLocalValue] = useState(value || "09:00");

  // Reset to default when opening
  useEffect(() => {
    if (open) {
      setLocalValue(value || "09:00");
      // Prevent body scroll
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
  }, [open, value]);

  const handlePresetClick = useCallback((time: string) => {
    vibrate(VIBRATION_PATTERNS.LIGHT);
    setLocalValue(time);
    onChange(time);
  }, [onChange, vibrate]);

  const handleTimeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = e.target.value;
    setLocalValue(newTime);
    onChange(newTime);
  }, [onChange]);

  const handleConfirm = useCallback(() => {
    vibrate(VIBRATION_PATTERNS.SUCCESS);
    onConfirm?.();
    onClose();
  }, [onClose, onConfirm, vibrate]);

  const handleCancel = useCallback(() => {
    vibrate(VIBRATION_PATTERNS.LIGHT);
    onClose();
  }, [onClose, vibrate]);

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

          {/* Sheet */}
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-50 flex items-end justify-center"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
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
                  Cancel
                </motion.button>
                <div className="flex items-center gap-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-[#a07060]">
                    <path d="M12 7v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10Z" stroke="currentColor" strokeWidth="2" />
                  </svg>
                  <span className="text-[#3d2b1f] text-sm font-semibold">Select Time</span>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleConfirm}
                  className="text-[#2e7d5e] text-sm font-semibold"
                >
                  Done
                </motion.button>
              </div>

              {/* Native Time Input */}
              <div className="px-6 py-6">
                <div className="flex flex-col items-center space-y-4">
                  <label className="text-[#9e8476] text-sm font-medium">Choose time</label>
                  <input
                    type="time"
                    value={localValue}
                    onChange={handleTimeChange}
                    className="w-full px-4 py-3 text-2xl text-center text-[#3d2b1f] font-semibold bg-[#f5f0e8] border-2 border-[#e8e0d0] rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50 focus:border-[#c4967a]"
                    style={{
                      WebkitAppearance: "none",
                      MozAppearance: "textfield",
                    }}
                  />
                  <div className="text-[#9e8476] text-xs font-medium">
                    {localValue}
                  </div>
                </div>
              </div>

              {/* Quick Presets */}
              <div className="border-t border-black/5 px-6 py-4">
                <div className="text-[#9e8476] text-xs font-medium mb-3">Quick times</div>
                <div className="grid grid-cols-5 gap-2">
                  {TIME_PRESETS.map((time) => {
                    const selected = localValue === time;
                    return (
                      <motion.button
                        key={time}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handlePresetClick(time)}
                        className={`py-2 rounded-lg text-xs font-medium transition-all
                          ${selected
                            ? "bg-[#2e7d5e] text-white shadow-md"
                            : "bg-[#f5f0e8] text-[#7c5340] hover:bg-[#e8e0d0]"
                          }
                        `}
                      >
                        {time}
                      </motion.button>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
