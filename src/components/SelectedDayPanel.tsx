import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format, isBefore, startOfDay } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Clock, Plus, Trash2, Save, X, Check, XCircle, StickyNote } from 'lucide-react';
import { vibrateLight, vibrateMedium, vibrateSuccess, vibrateError } from '../utils/vibration';
import type { AdminWorkDay, AdminBooking } from '../api/client';

interface SelectedDayPanelProps {
  date: Date;
  workDay: AdminWorkDay | null;
  onAddSlot: (time: string) => Promise<{ success: boolean; message?: string }>;
  onCreateWorkDay: (date: string) => Promise<{ success: boolean; message?: string }>;
  onDeleteSlot: (time: string) => Promise<{ success: boolean; message?: string }>;
  onUpdateClient: (data: {
    name: string;
    phone: string;
    date: string;
    time: string;
    username?: string;
    note?: string;
    status?: string;
    admin_note?: string;
  }) => Promise<{ success: boolean; message?: string; data?: { type: string; username: string; text: string } }>;
  onDeleteClient: (time: string) => Promise<{ success: boolean; message?: string }>;
  onRefresh: () => void;
}

function SelectedDayPanel({ 
  date, 
  workDay, 
  onAddSlot, 
  onCreateWorkDay,
  onDeleteSlot, 
  onUpdateClient, 
  onDeleteClient,
  onRefresh 
}: SelectedDayPanelProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [newSlotTime, setNewSlotTime] = useState('');
  const [editingSlot, setEditingSlot] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    phone: '',
    time: '',
    username: '',
    note: '',
    admin_note: ''
  });
  const [isSaving, setIsSaving] = useState(false);
  const isPast = isBefore(startOfDay(date), startOfDay(new Date()));

  const slots = workDay?.slots || [];

  const getClientForSlot = (time: string): AdminBooking | undefined => {
    return slots.find(s => s.time === time)?.booking;
  };

  const handleEdit = (time: string) => {
    const client = getClientForSlot(time);
    setEditForm({
      name: client?.client_name || '',
      phone: client?.phone || '',
      time: time,
      username: client?.username || '',
      note: client?.note || '',
      admin_note: client?.admin_note || ''
    });
    setEditingSlot(time);
    vibrateLight();
  };

  const handleSave = async () => {
    if (!editingSlot) return;
    setIsSaving(true);
    const dateStr = format(date, 'yyyy-MM-dd');
    const result = await onUpdateClient({
      name: editForm.name,
      phone: editForm.phone,
      date: dateStr,
      time: editForm.time,
      username: editForm.username || undefined,
      note: editForm.note || undefined,
      admin_note: editForm.admin_note || undefined,
    });
    if (result.success) {
      vibrateSuccess();
      setEditingSlot(null);
      if (result.data?.type === 'open_chat') {
        const telegramUrl = `https://t.me/${result.data.username}?text=${encodeURIComponent(result.data.text)}`;
        if (window.Telegram?.WebApp?.openTelegramLink) {
          window.Telegram.WebApp.openTelegramLink(telegramUrl);
        } else {
          window.open(telegramUrl, '_blank');
        }
      } else {
        setTimeout(onRefresh, 300);
      }
    } else {
      vibrateError();
    }
    setIsSaving(false);
  };

  const handleCancel = () => {
    setEditingSlot(null);
    setEditForm({ name: '', phone: '', time: '', username: '', note: '', admin_note: '' });
    vibrateLight();
  };

  const handleAddSlot = async (time: string) => {
    const result = await onAddSlot(time);
    if (result.success) {
      vibrateSuccess();
      setPickerOpen(false);
      setNewSlotTime('');
      onRefresh();
    } else if (result.message?.includes('не найден') || result.message?.includes('not found')) {
      const dateStr = format(date, 'yyyy-MM-dd');
      const createResult = await onCreateWorkDay(dateStr);
      if (createResult.success) {
        const retryResult = await onAddSlot(time);
        if (retryResult.success) {
          vibrateSuccess();
          setPickerOpen(false);
          setNewSlotTime('');
          onRefresh();
        } else {
          vibrateError();
        }
      } else {
        vibrateError();
      }
    } else {
      vibrateError();
    }
  };

  const handleDeleteSlot = async (time: string) => {
    const result = await onDeleteSlot(time);
    if (result.success) { vibrateSuccess(); onRefresh(); }
    else { vibrateError(); }
  };

  const handleDeleteClient = async (time: string) => {
    const result = await onDeleteClient(time);
    if (result.success) { vibrateSuccess(); onRefresh(); }
    else { vibrateError(); }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className="liquid-glass rounded-2xl p-4"
    >
      {/* ── Panel header ── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock size={15} className="text-[#c4967a]" />
          <span className="text-[#3d2b1f] text-sm font-semibold capitalize">
            {format(date, 'd MMMM', { locale: ru })}
          </span>
          {isPast && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#8b7355]/15 text-[#8b7355] font-medium">
              Прошедший
            </span>
          )}
        </div>
        {!isPast && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.92 }}
            onClick={() => {
              vibrateMedium();
              setPickerOpen(v => !v);
              if (!pickerOpen) setNewSlotTime('');
            }}
            className="liquid-glass-nav h-9 px-4 rounded-xl flex items-center gap-1.5
              text-[#7c5340] text-xs font-semibold hover:text-[#3d2b1f] transition-colors"
          >
            <Plus size={13} strokeWidth={2.5} />
            <span>Слот</span>
          </motion.button>
        )}
      </div>

      {/* ── Time Picker ── */}
      <AnimatePresence>
        {pickerOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-3"
          >
            <div className="flex gap-2">
              <input
                type="time" step="900"
                value={newSlotTime}
                onChange={(e) => setNewSlotTime(e.target.value)}
                className="liquid-glass-input flex-1 px-3 py-2 rounded-xl text-[#3d2b1f] text-sm"
              />
              <motion.button
                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={async () => { if (newSlotTime) await handleAddSlot(newSlotTime); }}
                disabled={!newSlotTime}
                className="btn-primary px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
              >
                Добавить
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={() => { setPickerOpen(false); setNewSlotTime(''); }}
                className="liquid-glass-nav px-4 py-2 rounded-xl text-sm font-medium text-[#7c5340]"
              >
                Отмена
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Slots list ── */}
      <div className="flex flex-col gap-2 mt-4">
        {slots.length === 0 ? (
          <p className="text-center text-[#9e8476] text-xs py-4">
            {isPast ? 'Нет записей за этот день' : 'Нет слотов — нажмите «+ Слот»'}
          </p>
        ) : (
          slots.sort((a, b) => a.time.localeCompare(b.time)).map((slot) => {
            const client = slot.booking;
            const isBooked = !!client;
            const isEditing = editingSlot === slot.time;

            return (
              <div key={slot.time} className="overflow-hidden">
                {isEditing ? (
                  /* ── Edit form ── */
                  <div className="liquid-glass p-3 rounded-xl space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                    <input
                      type="text" value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      placeholder="Имя клиента"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <input
                      type="tel" value={editForm.phone}
                      onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                      placeholder="Телефон"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <input
                      type="text" value={editForm.username}
                      onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                      placeholder="@username (опционально)"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <input
                      type="text" value={editForm.note}
                      onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                      placeholder="Заметка клиента"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    {/* Admin note — always available */}
                    <div className="relative">
                      <div className="flex items-center gap-1.5 mb-1">
                        <StickyNote size={11} className="text-[#8b7355]" />
                        <span className="text-[10px] font-medium text-[#8b7355] uppercase tracking-wider">
                          заметка для тебя
                        </span>
                      </div>
                      <textarea
                        value={editForm.admin_note}
                        onChange={(e) => setEditForm({ ...editForm, admin_note: e.target.value })}
                        placeholder="Например: клиент не пришёл, опоздал на 20 мин, попросила другой эффект..."
                        rows={2}
                        className="w-full px-3 py-2 rounded-lg bg-[#fef3c7]/30 border border-[#f59e0b]/20
                          text-[#3d2b1f] text-sm placeholder-[#9e8476]
                          focus:outline-none focus:ring-2 focus:ring-[#f59e0b]/30 resize-none"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleSave(); }}
                        className="flex-1 py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all duration-200 btn-primary hover:scale-105 active:scale-95"
                      >
                        <Save size={12} />
                        Сохранить
                      </button>
                      <button
                        onClick={handleCancel}
                        className="flex-1 liquid-glass-nav py-2 rounded-lg text-xs font-medium text-[#7c5340] flex items-center justify-center gap-1.5 hover:scale-105 active:scale-95 transition-all duration-200"
                      >
                        <X size={12} />
                        Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  /* ── Slot row ── */
                  <div
                    onClick={() => {
                      // Past: click edits admin_note. Future: click edits booking.
                      if (isPast && isBooked) {
                        handleEdit(slot.time);
                      } else if (!isBooked || client.status === 'confirmed' || client.status === 'pending') {
                        handleEdit(slot.time);
                      }
                    }}
                    className={`liquid-glass p-3 rounded-xl flex items-center justify-between cursor-pointer ${
                      isBooked ? 'bg-white/40 border border-[#c4967a]/20' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3 flex-1">
                      {isBooked ? (
                        <>
                          <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-xs font-semibold ${
                            isPast
                              ? 'bg-[#f5f0eb] border border-[#d4c5b5]/30 text-[#8b7355]'
                              : 'bg-[rgba(255,244,234,0.85)] border border-white/40 text-[#8b6049]'
                          }`}>
                            {client.client_name[0]}
                          </div>
                          <div className="flex-1 min-w-0">
                            {client.username ? (
                              <a
                                href={`https://t.me/${client.username}`}
                                target="_blank" rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className={`text-sm font-semibold leading-tight truncate hover:underline transition-colors ${
                                  isPast ? 'text-[#8b7355] hover:text-[#c4967a]' : 'text-[#3d2b1f] hover:text-[#c4967a]'
                                }`}
                              >
                                {client.client_name}
                              </a>
                            ) : (
                              <p className={`text-sm font-semibold leading-tight truncate ${
                                isPast ? 'text-[#8b7355]' : 'text-[#3d2b1f]'
                              }`}>{client.client_name}</p>
                            )}
                            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                              <p className={`text-xs ${isPast ? 'text-[#b8a494]' : 'text-[#9e8476]'}`}>{slot.time}</p>
                              {client.username && (
                                <a
                                  href={`https://t.me/${client.username}`}
                                  target="_blank" rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-[#2e7d5e] text-[10px] font-medium hover:underline"
                                >
                                  @{client.username}
                                </a>
                              )}
                              {client.status === 'pending' && (
                                <span className="text-[10px] text-[#ef4444] font-medium">Ожидает</span>
                              )}
                              {client.status === 'confirmed' && !client.admin_note && !isPast && (
                                <span className="text-[10px] text-[#2e7d5e] font-medium">Подтвержден</span>
                              )}
                              {client.admin_note && (
                                <span
                                  className={`text-[10px] font-medium flex items-center gap-0.5 ml-1 ${
                                    isPast ? 'text-[#8b7355]' : 'text-[#f59e0b]'
                                  }`}
                                  title={client.admin_note}
                                >
                                  <StickyNote size={10} />
                                  {client.admin_note.length > 25
                                    ? client.admin_note.slice(0, 25) + '…'
                                    : client.admin_note}
                                </span>
                              )}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="flex items-center gap-2 flex-1">
                          <Clock size={14} className="text-[#a07060]" />
                          <span className={`text-sm font-medium ${isPast ? 'text-[#b8a494]' : 'text-[#3d2b1f]'}`}>
                            {slot.time}
                          </span>
                          <span className="text-[10px] text-[#9e8476]">Свободно</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {isBooked ? (
                        <>
                          {/* Past day: sticky-note button */}
                          {isPast && (
                            <motion.button
                              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                              onClick={(e) => { e.stopPropagation(); handleEdit(slot.time); }}
                              className="h-7 w-7 rounded-lg flex items-center justify-center text-[#c4967a] hover:bg-[#c4967a]/10 transition-colors"
                              title="Заметка"
                            >
                              <StickyNote size={13} />
                            </motion.button>
                          )}
                          {/* Pending actions (future only) */}
                          {!isPast && client.status === 'pending' && (
                            <>
                              <motion.button
                                whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  const dateStr = format(date, 'yyyy-MM-dd');
                                  const result = await onUpdateClient({
                                    name: client.client_name, phone: client.phone,
                                    date: dateStr, time: slot.time,
                                    username: client.username, note: client.note, status: 'confirmed',
                                  });
                                  if (result.success) {
                                    vibrateSuccess();
                                    if (result.data?.type === 'open_chat') {
                                      const telegramUrl = `https://t.me/${result.data.username}?text=${encodeURIComponent(result.data.text)}`;
                                      setTimeout(() => {
                                        if (window.Telegram?.WebApp?.openTelegramLink) {
                                          window.Telegram.WebApp.openTelegramLink(telegramUrl);
                                        } else { window.open(telegramUrl, '_blank'); }
                                      }, 500);
                                    } else if (client.username) {
                                      const msg = `✅ Записала\n\n📅 Дата: ${dateStr}\n🕐 Время: ${slot.time}\n📍 Адрес: Тихий переулок, 4\n\n📹 Видео: https://t.me/lashessoto4ka/8`;
                                      const url = `https://t.me/${client.username.replace('@','')}?text=${encodeURIComponent(msg)}`;
                                      setTimeout(() => {
                                        if (window.Telegram?.WebApp?.openTelegramLink) {
                                          window.Telegram.WebApp.openTelegramLink(url);
                                        } else { window.open(url, '_blank'); }
                                      }, 500);
                                    }
                                    onRefresh();
                                  } else { vibrateError(); }
                                }}
                                className="h-7 w-7 rounded-lg flex items-center justify-center bg-[#2e7d5e] text-white hover:scale-105 active:scale-95 transition-all duration-200"
                                title="Подтвердить"
                              >
                                <Check size={12} />
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  const result = await onDeleteClient(slot.time);
                                  if (result.success) { vibrateSuccess(); onRefresh(); }
                                  else { vibrateError(); }
                                }}
                                className="h-7 w-7 rounded-lg flex items-center justify-center bg-[#ef4444] text-white hover:scale-105 active:scale-95 transition-all duration-200"
                                title="Отклонить"
                              >
                                <XCircle size={12} />
                              </motion.button>
                            </>
                          )}
                          {/* Delete button — past days too */}
                          <motion.button
                            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                            onClick={(e) => { e.stopPropagation(); handleDeleteClient(slot.time); }}
                            className="h-7 w-7 rounded-lg flex items-center justify-center text-[#ef4444] hover:bg-red-500/10 transition-colors"
                            title="Удалить запись"
                          >
                            <Trash2 size={12} />
                          </motion.button>
                        </>
                      ) : (
                        !isPast && (
                          <motion.button
                            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                            onClick={(e) => { e.stopPropagation(); handleDeleteSlot(slot.time); }}
                            className="h-7 w-7 rounded-lg flex items-center justify-center text-[#ef4444] hover:bg-red-500/10 transition-colors"
                            title="Удалить слот"
                          >
                            <Trash2 size={12} />
                          </motion.button>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </motion.div>
  );
}

export default SelectedDayPanel;
