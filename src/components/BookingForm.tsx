// ============================================================
// src/components/BookingForm.tsx — Форма записи клиента
// ============================================================

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Phone, User, AlertCircle } from 'lucide-react';
import { CONTACT_INFO, MESSAGE_TEMPLATES } from '../config';
import { apiClient } from '../api/client';
import { vibrateSuccess, vibrateError, vibrateWarning } from '../utils/vibration';

interface BookingFormProps {
  date: Date;
  time: string;
  availableSlots: string[];
  onTimeChange: (time: string) => void;
  onClose: () => void;
}

const PHONE_REGEX = /^(\+7|8|7)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$/;
const USERNAME_REGEX = /^[a-zA-Z0-9_]{5,32}$/;

function validatePhone(phone: string): { valid: boolean; message?: string } {
  if (!phone || !phone.trim()) return { valid: true }; // Optional
  const digits = phone.replace(/\D/g, '');
  if (digits.length !== 11) {
    return { valid: false, message: 'Номер должен содержать 11 цифр (например: +7 978 423-74-53)' };
  }
  if (!PHONE_REGEX.test(phone)) {
    return { valid: false, message: 'Неверный формат. Используйте: +7 978 423-74-53' };
  }
  return { valid: true };
}

function validateUsername(username: string): { valid: boolean; message?: string } {
  if (!username || !username.trim()) return { valid: true }; // Optional
  if (!USERNAME_REGEX.test(username)) {
    return { valid: false, message: 'Username должен содержать только буквы, цифры и подчеркивания (5-32 символа)' };
  }
  return { valid: true };
}

function formatDateRu(date: Date): string {
  const months = [
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
  ];
  return `${date.getDate()} ${months[date.getMonth()]}`;
}

export default function BookingForm({
  date,
  time,
  availableSlots,
  onTimeChange,
  onClose,
}: BookingFormProps) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [autoFilled, setAutoFilled] = useState(false);
  const [username, setUsername] = useState('');
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [isTelegram, setIsTelegram] = useState(false);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg?.initDataUnsafe?.user) {
      const user = tg.initDataUnsafe.user;
      const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ');
      if (fullName) {
        setName(fullName);
        setAutoFilled(true);
      }
      if (user.username) {
        setUsername(user.username);
      }
      setIsTelegram(true);
    }
  }, []);

  function handlePhoneChange(val: string) {
    setPhone(val);
    if (phoneError) {
      const v = validatePhone(val);
      if (v.valid) setPhoneError(null);
    }
  }

  function handlePhoneBlur() {
    const v = validatePhone(phone);
    if (!v.valid) {
      setPhoneError(v.message || null);
      vibrateWarning();
    } else {
      setPhoneError(null);
    }
  }

  function handleUsernameChange(val: string) {
    setUsername(val);
    if (usernameError) {
      const v = validateUsername(val);
      if (v.valid) setUsernameError(null);
    }
  }

  function handleUsernameBlur() {
    const v = validateUsername(username);
    if (!v.valid) {
      setUsernameError(v.message || null);
      vibrateWarning();
    } else {
      setUsernameError(null);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // Validate phone
    const phoneValidation = validatePhone(phone);
    if (!phoneValidation.valid) {
      setPhoneError(phoneValidation.message || null);
      vibrateError();
      return;
    }

    // Validate username (only if not in Telegram)
    if (!isTelegram) {
      const usernameValidation = validateUsername(username);
      if (!usernameValidation.valid) {
        setUsernameError(usernameValidation.message || null);
        vibrateError();
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const tg = window.Telegram?.WebApp;
      const telegramUser = tg?.initDataUnsafe?.user;

      const result = await apiClient.createBooking({
        name,
        phone: phone.trim() || undefined,
        date: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
        time,
        service_id: 'classic',
        user_id: telegramUser?.id,
        username: username || undefined,
      });

      if (!result.success) {
        vibrateError();
        alert(`Ошибка: ${result.message}`);
        setIsSubmitting(false);
        return;
      }

      vibrateSuccess();
      setIsSuccess(true);

      // Open DM with admin
      const message = MESSAGE_TEMPLATES.CLIENT_BOOKING_FORM({
        name,
        phone: phone.trim() || undefined,
        date: formatDateRu(date),
        time,
      });

      const adminUsername = CONTACT_INFO.ADMIN_USERNAME.replace('@', '');
      const telegramUrl = `https://t.me/${adminUsername}?text=${encodeURIComponent(message)}`;

      // Delay to show success state
      setTimeout(() => {
        // Use window.open to support ?text= parameter
        // tg.openTelegramLink doesn't support text parameter for security reasons
        console.log('[BookingForm] Opening Telegram URL:', telegramUrl);
        const opened = window.open(telegramUrl, '_blank');
        if (!opened) {
          console.warn('[BookingForm] window.open blocked or failed, trying location.href');
          window.location.href = telegramUrl;
        }
        // Close modal after opening chat
        setTimeout(() => onClose(), 500);
      }, 1200);
    } catch {
      vibrateError();
      alert('Ошибка при создании записи. Попробуйте позже.');
      setIsSubmitting(false);
    }
  }

  return (
    <div className="liquid-glass rounded-2xl p-4">
      <h3 className="text-base font-semibold text-[#3d2b1f] mb-3">
        Оформление записи
      </h3>

      {/* Selected date & time summary */}
      <div className="mb-3 p-3 bg-white/30 rounded-xl flex items-center gap-3">
        <div className="text-center flex-1">
          <p className="text-xs text-[#9e8476]">Дата</p>
          <p className="text-sm font-semibold text-[#3d2b1f]">{formatDateRu(date)}</p>
        </div>
        <div className="w-px h-8 bg-[#c4967a]/20" />
        <div className="text-center flex-1">
          <p className="text-xs text-[#9e8476]">Время</p>
          <p className="text-sm font-semibold text-[#3d2b1f]">{time}</p>
        </div>
      </div>

      {/* Slot switcher (if multiple slots) */}
      {availableSlots.length > 1 && (
        <div className="mb-3">
          <p className="text-xs text-[#9e8476] mb-2">Изменить время:</p>
          <div className="flex flex-wrap gap-1.5">
            {availableSlots.map((slot) => (
              <button
                key={slot}
                type="button"
                onClick={() => onTimeChange(slot)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all active:scale-95 ${
                  time === slot
                    ? 'bg-[#c4967a] text-white shadow-sm'
                    : 'bg-white/50 text-[#3d2b1f] hover:bg-white/70 border border-white/60'
                }`}
              >
                {slot}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Name */}
        <div>
          <label className="block text-xs font-medium text-[#7c5340] mb-1.5">
            Ваше имя *
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9e8476] w-4 h-4" />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="liquid-glass-input w-full pl-9 pr-4 py-2.5 rounded-xl text-[#3d2b1f] text-sm
                placeholder:text-[#9e8476]/60"
              placeholder="Введите имя"
            />
          </div>
          {autoFilled && (
            <p className="text-[10px] text-emerald-600 mt-1 flex items-center gap-1">
              <Check size={10} /> Автозаполнено из Telegram
            </p>
          )}
        </div>

        {/* Phone (optional) */}
        <div>
          <label className="block text-xs font-medium text-[#7c5340] mb-1.5">
            Телефон{' '}
            <span className="text-[#9e8476] font-normal">(необязательно)</span>
          </label>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9e8476] w-4 h-4" />
            <input
              type="tel"
              value={phone}
              onChange={(e) => handlePhoneChange(e.target.value)}
              onBlur={handlePhoneBlur}
              className={`liquid-glass-input w-full pl-9 pr-4 py-2.5 rounded-xl text-[#3d2b1f] text-sm
                placeholder:text-[#9e8476]/60 ${
                  phoneError ? 'border-red-300 focus:border-red-400' : ''
                }`}
              placeholder="+7 978 423-74-53"
            />
          </div>
          <AnimatePresence>
            {phoneError ? (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="text-[10px] text-red-500 mt-1 flex items-center gap-1"
              >
                <AlertCircle size={10} /> {phoneError}
              </motion.p>
            ) : (
              <p className="text-[10px] text-[#9e8476] mt-1">
                Формат: +7 978 423-74-53 (11 цифр)
              </p>
            )}
          </AnimatePresence>
        </div>

        {/* Username (only if not in Telegram) */}
        {!isTelegram && (
          <div>
            <label className="block text-xs font-medium text-[#7c5340] mb-1.5">
              Telegram username{' '}
              <span className="text-[#9e8476] font-normal">(без @)</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9e8476] w-4 h-4" />
              <input
                type="text"
                value={username}
                onChange={(e) => handleUsernameChange(e.target.value)}
                onBlur={handleUsernameBlur}
                className={`liquid-glass-input w-full pl-9 pr-4 py-2.5 rounded-xl text-[#3d2b1f] text-sm
                  placeholder:text-[#9e8476]/60 ${
                  usernameError ? 'border-red-300 focus:border-red-400' : ''
                }`}
                placeholder="username"
              />
            </div>
            <AnimatePresence>
              {usernameError ? (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="text-[10px] text-red-500 mt-1 flex items-center gap-1"
                >
                  <AlertCircle size={10} /> {usernameError}
                </motion.p>
              ) : (
                <p className="text-[10px] text-[#9e8476] mt-1">
                  Нужно для отправки подтверждения в личные сообщения
                </p>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Submit button */}
        <motion.button
          type="submit"
          disabled={isSubmitting || !name.trim() || isSuccess}
          whileTap={{ scale: 0.97 }}
          className="w-full h-12 flex items-center justify-center gap-2 rounded-xl btn-primary
            font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSuccess ? (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex items-center gap-2"
            >
              <Check size={18} />
              Заявка создана! ✨
            </motion.span>
          ) : isSubmitting ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spinner" />
              Отправка...
            </>
          ) : (
            <>
              <Check size={18} />
              Записаться
            </>
          )}
        </motion.button>

        {!isSuccess && (
          <p className="text-[10px] text-[#9e8476] text-center">
            После создания заявки вы будете перенаправлены в чат с мастером
          </p>
        )}
      </form>
    </div>
  );
}
