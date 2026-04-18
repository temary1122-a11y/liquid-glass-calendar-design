// ============================================================
// src/components/BookingForm.tsx — Форма записи
// ============================================================

import { useState, useEffect } from 'react';
import { Check, Phone, User } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface BookingFormProps {
  date: Date;
  time: string;
  availableSlots: string[];
  onTimeChange: (time: string) => void;
  onClose: () => void;
}

export default function BookingForm({ date, time, availableSlots, onTimeChange, onClose }: BookingFormProps) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [autoFilled, setAutoFilled] = useState(false);

  // Автозаполнение данных из Telegram WebApp
  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      const tg = window.Telegram.WebApp;

      // Получаем имя пользователя
      if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ');
        if (fullName) {
          setName(fullName);
          setAutoFilled(true);
        }
      }
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Формируем сообщение для Telegram
      const message = `Здравствуйте, запишите пожалуйста на ${format(date, 'd MMMM', { locale: ru })} на ${time}`;
      
      // Перенаправляем в личные сообщения администратора
      // TODO: Заменить на реальный username администратора
      const adminUsername = 'admin_username'; // Заменить на реальный
      const telegramUrl = `https://t.me/${adminUsername}?text=${encodeURIComponent(message)}`;
      window.open(telegramUrl, '_blank');
      
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white/95 backdrop-blur-xl rounded-t-3xl p-6 border-t border-white/30">
      <h3 className="text-lg font-semibold text-[#3d2b1f] mb-4">Оформление записи</h3>

      {/* Информация о записи */}
      <div className="mb-4 p-4 bg-white/30 rounded-xl">
        <p className="text-sm text-[#9e8476]">Дата: <span className="font-medium text-[#3d2b1f]">{format(date, 'd MMMM', { locale: ru })}</span></p>
        <p className="text-sm text-[#9e8476] mt-1">Время: <span className="font-medium text-[#3d2b1f]">{time}</span></p>
      </div>

      {/* Селектор доступных слотов */}
      <div className="mb-4 p-4 bg-white/30 rounded-xl">
        <p className="text-xs text-[#9e8476] mb-3">Выберите время:</p>
        <div className="flex flex-wrap gap-2">
          {availableSlots.map(slot => (
            <button
              key={slot}
              type="button"
              onClick={() => onTimeChange(slot)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${time === slot 
                  ? 'bg-[#c4967a] text-white' 
                  : 'bg-white/50 text-[#3d2b1f] hover:bg-white/70'
                }`}
            >
              {slot}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-[#3d2b1f] mb-2">
            Ваше имя
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#9e8476] w-5 h-5" />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/50 border border-white/30 focus:border-[#7c5340]/50 focus:outline-none focus:ring-2 focus:ring-[#7c5340]/20 text-[#3d2b1f] placeholder-[#9e8476]/50 transition-all"
              placeholder="Введите имя"
            />
          </div>
          {autoFilled && (
            <p className="text-xs text-[#2e7d5e] mt-1">✓ Автозаполнено из Telegram</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-[#3d2b1f] mb-2">
            Телефон
          </label>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#9e8476] w-5 h-5" />
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/50 border border-white/30 focus:border-[#7c5340]/50 focus:outline-none focus:ring-2 focus:ring-[#7c5340]/20 text-[#3d2b1f] placeholder-[#9e8476]/50 transition-all"
              placeholder="+7 (999) 999-99-99"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || !name || !phone}
          className="w-full h-14 flex items-center justify-center gap-2 rounded-xl bg-[#c4967a] text-white font-semibold hover:bg-[#b0856a] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
        >
          {isSubmitting ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Отправка...</span>
            </>
          ) : (
            <>
              <Check className="w-5 h-5" />
              Записаться
            </>
          )}
        </button>
      </form>
    </div>
  );
}
