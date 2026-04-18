// ============================================================
// src/components/Toast.tsx — Компонент уведомлений
// ============================================================

import { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { motion } from 'framer-motion';

interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  onClose: () => void;
  duration?: number;
}

export default function Toast({ message, type = 'success', onClose, duration = 3000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-[#2e7d5e]" />,
    error: <AlertCircle className="w-5 h-5 text-[#c4967a]" />,
    info: <Info className="w-5 h-5 text-[#c4967a]" />,
  };

  const colors = {
    success: 'border-[#2e7d5e] bg-[#2e7d5e]/10',
    error: 'border-[#c4967a] bg-[#c4967a]/10',
    info: 'border-[#c4967a] bg-[#c4967a]/10',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 100 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 100 }}
      className={`
        fixed top-4 right-4 z-50
        flex items-center gap-3 px-4 py-3
        rounded-xl shadow-lg border-l-4 backdrop-blur-xl
        ${colors[type]}
        liquid-glass-calendar
      `}
    >
      {icons[type]}
      <span className="text-sm font-medium text-[#3d2b1f]">{message}</span>
      <button
        onClick={onClose}
        className="ml-2 text-[#9e8476] hover:text-[#3d2b1f] transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}
