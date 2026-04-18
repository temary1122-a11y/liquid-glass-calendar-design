// ============================================================
// src/components/TimePicker.tsx — iOS-style Time Picker
// ============================================================

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface TimePickerProps {
  value: string;
  onChange: (time: string) => void;
  onClose: () => void;
}

export default function TimePicker({ value, onChange, onClose }: TimePickerProps) {
  const [hours, setHours] = useState(0);
  const [minutes, setMinutes] = useState(0);
  
  const hourOptions = Array.from({ length: 24 }, (_, i) => i);
  const minuteOptions = [0, 15, 30, 45];
  
  useEffect(() => {
    if (value) {
      const [h, m] = value.split(':').map(Number);
      setHours(h);
      setMinutes(m);
    }
  }, [value]);
  
  const handleVibrate = () => {
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
  };
  
  const handleHourSelect = (hour: number) => {
    handleVibrate();
    setHours(hour);
    updateTime(hour, minutes);
  };
  
  const handleMinuteSelect = (minute: number) => {
    handleVibrate();
    setMinutes(minute);
    updateTime(hours, minute);
  };
  
  const updateTime = (h: number, m: number) => {
    const timeStr = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    onChange(timeStr);
  };
  
  const formatHour = (h: number) => String(h).padStart(2, '0');
  const formatMinute = (m: number) => String(m).padStart(2, '0');
  
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
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onClose}
            className="text-[#c4967a] text-sm font-semibold"
          >
            Отмена
          </button>
          <h3 className="text-[#3d2b1f] text-base font-semibold">Выберите время</h3>
          <button
            onClick={onClose}
            className="text-[#2e7d5e] text-sm font-semibold"
          >
            Готово
          </button>
        </div>
        
        {/* Picker */}
        <div className="relative h-[200px] flex">
          {/* Gradient masks */}
          <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-white/90 to-transparent pointer-events-none z-10 rounded-t-2xl" />
          <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-white/90 to-transparent pointer-events-none z-10 rounded-b-2xl" />
          
          {/* Selection indicator */}
          <div className="absolute top-1/2 left-0 right-0 h-10 -translate-y-1/2 border-y border-[#c4967a]/30 bg-[#c4967a]/5 z-0" />
          
          {/* Hours column */}
          <div className="flex-1 overflow-hidden relative">
            <div className="absolute inset-0 overflow-y-auto scrollbar-hide">
              <div className="py-[80px]">
                {hourOptions.map((hour) => (
                  <motion.button
                    key={hour}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleHourSelect(hour)}
                    className={`
                      w-full h-10 flex items-center justify-center text-lg font-medium
                      transition-all duration-200
                      ${hours === hour 
                        ? 'text-[#3d2b1f] font-semibold scale-110' 
                        : 'text-[#9e8476] scale-100'
                      }
                    `}
                  >
                    {formatHour(hour)}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
          
          {/* Separator */}
          <div className="w-8 flex items-center justify-center">
            <span className="text-2xl text-[#c4967a] font-light">:</span>
          </div>
          
          {/* Minutes column */}
          <div className="flex-1 overflow-hidden relative">
            <div className="absolute inset-0 overflow-y-auto scrollbar-hide">
              <div className="py-[80px]">
                {minuteOptions.map((minute) => (
                  <motion.button
                    key={minute}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleMinuteSelect(minute)}
                    className={`
                      w-full h-10 flex items-center justify-center text-lg font-medium
                      transition-all duration-200
                      ${minutes === minute 
                        ? 'text-[#3d2b1f] font-semibold scale-110' 
                        : 'text-[#9e8476] scale-100'
                      }
                    `}
                  >
                    {formatMinute(minute)}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
