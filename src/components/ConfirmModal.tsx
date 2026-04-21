// ============================================================
// src/components/ConfirmModal.tsx — Модальное окно подтверждения
// ============================================================

import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import { vibrateWarning } from '../utils/vibration';
import { useEffect } from 'react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  warning?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export default function ConfirmModal({
  isOpen,
  title,
  message,
  warning,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  onConfirm,
  onCancel,
  danger = false,
}: ConfirmModalProps) {
  useEffect(() => {
    if (isOpen) vibrateWarning();
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex items-end justify-center p-4 overlay-backdrop"
          onClick={onCancel}
        >
          <motion.div
            key="modal-content"
            initial={{ opacity: 0, y: 60, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.97 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="liquid-glass rounded-3xl p-6 w-full max-w-sm"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Icon */}
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                  danger ? 'bg-red-100' : 'bg-amber-100'
                }`}
              >
                <AlertTriangle
                  size={20}
                  className={danger ? 'text-red-500' : 'text-amber-500'}
                />
              </div>
              <h3 className="text-lg font-semibold text-[#3d2b1f]">{title}</h3>
            </div>

            {/* Message */}
            <p className="text-[#7c5340] text-sm mb-3 leading-relaxed">{message}</p>

            {/* Warning */}
            {warning && (
              <div className="mb-4 p-3 bg-amber-50/70 rounded-xl border border-amber-200/50">
                <p className="text-amber-800 text-sm font-medium">⚠️ {warning}</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                onClick={onCancel}
                className="flex-1 py-3 rounded-xl liquid-glass-nav text-[#7c5340] font-medium text-sm transition-all active:scale-95"
              >
                {cancelText}
              </button>
              <button
                onClick={onConfirm}
                className={`flex-1 py-3 rounded-xl font-medium text-sm transition-all active:scale-95 ${
                  danger ? 'btn-danger' : 'btn-primary'
                }`}
              >
                {confirmText}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
