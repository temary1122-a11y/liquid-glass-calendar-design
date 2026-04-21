// ============================================================
// src/components/AdminSchedulePanel.tsx — Панель управления для мастера
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus, Trash2, User, Phone, Clock,
  Calendar, ChevronDown, ChevronUp,
  XCircle, Edit3, Save, X,
} from 'lucide-react';
import { apiClient, type AdminWorkDay } from '../api/client';
import { vibrateMedium, vibrateSuccess, vibrateError, vibrateLight } from '../utils/vibration';
import ConfirmModal from './ConfirmModal';

const MONTH_NAMES = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];



interface EditingClient {
  date: string;
  time: string;
  name: string;
  phone: string;
  username?: string;
  note?: string;
  isNew?: boolean;
}

interface DeleteTarget {
  date: string;
  time: string;
  clientName?: string;
}

function formatDateRu(dateStr: string): string {
  try {
    const [year, month, day] = dateStr.split('-').map(Number);
    return `${day} ${MONTH_NAMES[month - 1]} ${year}`;
  } catch {
    return dateStr;
  }
}

function getStatusLabel(status: string, isCancelled?: boolean): { label: string; className: string } {
  if (isCancelled) return { label: 'отменена', className: 'badge-cancelled' };
  switch (status) {
    case 'confirmed': return { label: 'подтверждена', className: 'badge-confirmed' };
    case 'pending': return { label: 'ожидает', className: 'badge-pending' };
    case 'completed': return { label: 'завершена', className: 'badge-completed' };
    case 'cancelled': return { label: 'отменена', className: 'badge-cancelled' };
    default: return { label: status || 'ожидает', className: 'badge-pending' };
  }
}

export default function AdminSchedulePanel() {
  const today = new Date();
  const [workDays, setWorkDays] = useState<Record<string, AdminWorkDay>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());

  // Slot management
  const [newSlotDate, setNewSlotDate] = useState('');
  const [newSlotTime, setNewSlotTime] = useState('');
  const [newWorkDay, setNewWorkDay] = useState('');

  // Client editing
  const [editingClient, setEditingClient] = useState<EditingClient | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Confirm modals
  const [deleteSlotTarget, setDeleteSlotTarget] = useState<{ date: string; time: string } | null>(null);
  const [deleteClientTarget, setDeleteClientTarget] = useState<DeleteTarget | null>(null);

  const loadData = useCallback(async (quiet = false) => {
    if (!quiet) setIsLoading(true);
    try {
      const data = await apiClient.getWorkDaysWithBookings();
      setWorkDays(data);
    } catch {
      console.error('Failed to load admin data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(true), 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  function toggleDay(dateKey: string) {
    vibrateLight();
    setExpandedDays((prev) => {
      const next = new Set(prev);
      if (next.has(dateKey)) next.delete(dateKey);
      else next.add(dateKey);
      return next;
    });
  }

  async function handleAddWorkDay() {
    if (!newWorkDay) return;
    vibrateMedium();
    const result = await apiClient.addWorkDay(newWorkDay);
    if (result.success) {
      vibrateSuccess();
      setNewWorkDay('');
      await loadData(true);
    } else {
      vibrateError();
      alert(result.message || 'Ошибка добавления дня');
    }
  }

  async function handleAddSlot() {
    if (!newSlotDate || !newSlotTime) return;
    vibrateMedium();
    const result = await apiClient.addTimeSlot(newSlotDate, newSlotTime);
    if (result.success) {
      vibrateSuccess();
      setNewSlotTime('');
      await loadData(true);
    } else {
      vibrateError();
      alert(result.message || 'Ошибка добавления слота');
    }
  }

  async function handleDeleteSlot() {
    if (!deleteSlotTarget) return;
    vibrateMedium();
    const result = await apiClient.deleteTimeSlot(deleteSlotTarget.date, deleteSlotTarget.time);
    if (result.success) {
      vibrateSuccess();
      await loadData(true);
    } else {
      vibrateError();
      alert(result.message || 'Не удалось удалить слот');
    }
    setDeleteSlotTarget(null);
  }

  async function handleDeleteClient() {
    if (!deleteClientTarget) return;
    vibrateMedium();
    const result = await apiClient.deleteClient(deleteClientTarget.date, deleteClientTarget.time);
    if (result.success) {
      vibrateSuccess();
      await loadData(true);
    } else {
      vibrateError();
      alert(result.message || 'Не удалось удалить запись');
    }
    setDeleteClientTarget(null);
  }

  async function handleSaveClient() {
    if (!editingClient) return;
    setIsSaving(true);
    vibrateMedium();
    try {
      let result;
      if (editingClient.isNew) {
        result = await apiClient.createClient({
          name: editingClient.name,
          phone: editingClient.phone,
          date: editingClient.date,
          time: editingClient.time,
          username: editingClient.username,
          note: editingClient.note,
        });
      } else {
        result = await apiClient.updateClient({
          name: editingClient.name,
          phone: editingClient.phone,
          date: editingClient.date,
          time: editingClient.time,
          username: editingClient.username,
          note: editingClient.note,
        });
      }

      if (result.success) {
        vibrateSuccess();
        setEditingClient(null);
        await loadData(true);
      } else {
        vibrateError();
        alert(result.message || 'Ошибка сохранения');
      }
    } finally {
      setIsSaving(false);
    }
  }

  const workDaysList = Object.values(workDays).sort((a, b) =>
    a.day_date.localeCompare(b.day_date)
  );

  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  const totalBookings = Object.values(workDays).reduce(
    (sum, day) => sum + day.slots.filter((s) => s.is_booked).length,
    0
  );

  return (
    <div className="space-y-4">
      {/* ── Stats bar ── */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Рабочих дней', value: workDaysList.length },
          { label: 'Всего слотов', value: Object.values(workDays).reduce((s, d) => s + d.slots.length, 0) },
          { label: 'Записей', value: totalBookings },
        ].map((stat) => (
          <div key={stat.label} className="liquid-glass rounded-xl p-3 text-center">
            <p className="text-xl font-bold text-[#3d2b1f]">{stat.value}</p>
            <p className="text-[10px] text-[#9e8476] mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* ── Add Work Day ── */}
      <div className="liquid-glass rounded-2xl p-4">
        <h3 className="text-sm font-semibold text-[#3d2b1f] mb-3 flex items-center gap-2">
          <Calendar size={15} className="text-[#c4967a]" />
          Добавить рабочий день
        </h3>
        <div className="flex gap-2">
          <input
            type="date"
            value={newWorkDay}
            onChange={(e) => setNewWorkDay(e.target.value)}
            min={todayKey}
            className="liquid-glass-input flex-1 px-3 py-2 rounded-xl text-[#3d2b1f] text-sm"
          />
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={handleAddWorkDay}
            disabled={!newWorkDay}
            className="btn-primary px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50 flex items-center gap-1.5"
          >
            <Plus size={15} />
            Добавить
          </motion.button>
        </div>
      </div>

      {/* ── Add Time Slot ── */}
      <div className="liquid-glass rounded-2xl p-4">
        <h3 className="text-sm font-semibold text-[#3d2b1f] mb-3 flex items-center gap-2">
          <Clock size={15} className="text-[#c4967a]" />
          Добавить слот
        </h3>
        <div className="flex gap-2 mb-2">
          <select
            value={newSlotDate}
            onChange={(e) => setNewSlotDate(e.target.value)}
            className="liquid-glass-input flex-1 px-3 py-2 rounded-xl text-[#3d2b1f] text-sm"
          >
            <option value="">Выберите дату</option>
            {workDaysList.map((day) => (
              <option key={day.day_date} value={day.day_date}>
                {formatDateRu(day.day_date)}
              </option>
            ))}
          </select>
          <input
            type="time"
            value={newSlotTime}
            onChange={(e) => setNewSlotTime(e.target.value)}
            className="liquid-glass-input px-3 py-2 rounded-xl text-[#3d2b1f] text-sm w-28"
          />
        </div>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleAddSlot}
          disabled={!newSlotDate || !newSlotTime}
          className="w-full btn-primary py-2.5 rounded-xl text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Plus size={15} />
          Добавить слот
        </motion.button>
      </div>

      {/* ── Work Days List ── */}
      <div className="liquid-glass rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-[#3d2b1f] flex items-center gap-2">
            <Calendar size={15} className="text-[#c4967a]" />
            Расписание
          </h3>
          <button
            onClick={() => loadData(true)}
            className="text-xs text-[#9e8476] px-2 py-1 rounded-lg liquid-glass-nav"
          >
            Обновить
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-[#c4967a]/30 border-t-[#c4967a] rounded-full spinner" />
          </div>
        ) : workDaysList.length === 0 ? (
          <p className="text-sm text-[#9e8476] text-center py-6">
            Нет рабочих дней. Добавьте первый рабочий день выше.
          </p>
        ) : (
          <div className="space-y-2">
            {workDaysList.map((day) => {
              const isExpanded = expandedDays.has(day.day_date);
              const bookedCount = day.slots.filter((s) => s.is_booked).length;
              const totalSlots = day.slots.length;

              return (
                <div key={day.day_date} className="liquid-glass-calendar rounded-xl overflow-hidden">
                  {/* Day header */}
                  <button
                    onClick={() => toggleDay(day.day_date)}
                    className="w-full p-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-left">
                        <p className="text-sm font-semibold text-[#3d2b1f]">
                          {formatDateRu(day.day_date)}
                        </p>
                        <p className="text-[10px] text-[#9e8476]">
                          {bookedCount}/{totalSlots} записей
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {bookedCount > 0 && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full badge-confirmed font-medium">
                          {bookedCount} чел.
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronUp size={16} className="text-[#9e8476]" />
                      ) : (
                        <ChevronDown size={16} className="text-[#9e8476]" />
                      )}
                    </div>
                  </button>

                  {/* Day detail */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        key={`detail-${day.day_date}`}
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="px-3 pb-3 border-t border-white/30 pt-2 space-y-2">
                          {day.slots.length === 0 ? (
                            <p className="text-xs text-[#9e8476] text-center py-2">
                              Нет слотов. Добавьте выше.
                            </p>
                          ) : (
                            day.slots.map((slot) => {
                              const badge = slot.booking
                                ? getStatusLabel(slot.booking.status)
                                : null;

                              return (
                                <div
                                  key={slot.time}
                                  className={`rounded-xl p-2.5 ${
                                    slot.is_booked
                                      ? 'bg-white/40 border border-[#c4967a]/20'
                                      : 'bg-white/20'
                                  }`}
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <Clock size={12} className="text-[#c4967a]" />
                                      <span className="text-sm font-semibold text-[#3d2b1f]">
                                        {slot.time}
                                      </span>
                                      {badge && (
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${badge.className}`}>
                                          {badge.label}
                                        </span>
                                      )}
                                    </div>

                                    <div className="flex items-center gap-1.5">
                                      {slot.is_booked && slot.booking && (
                                        <button
                                          onClick={() => {
                                            vibrateLight();
                                            setEditingClient({
                                              date: day.day_date,
                                              time: slot.time,
                                              name: slot.booking!.client_name,
                                              phone: slot.booking!.phone,
                                              username: slot.booking!.username,
                                              note: slot.booking!.note,
                                            });
                                          }}
                                          className="w-7 h-7 flex items-center justify-center rounded-lg
                                            bg-blue-50 text-blue-500 hover:bg-blue-100 transition-colors"
                                        >
                                          <Edit3 size={13} />
                                        </button>
                                      )}

                                      {!slot.is_booked && (
                                        <button
                                          onClick={() => {
                                            vibrateLight();
                                            setEditingClient({
                                              date: day.day_date,
                                              time: slot.time,
                                              name: '',
                                              phone: '',
                                              isNew: true,
                                            });
                                          }}
                                          className="w-7 h-7 flex items-center justify-center rounded-lg
                                            bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors"
                                        >
                                          <User size={13} />
                                        </button>
                                      )}

                                      <button
                                        onClick={() => setDeleteSlotTarget({ date: day.day_date, time: slot.time })}
                                        className="w-7 h-7 flex items-center justify-center rounded-lg
                                          bg-red-50 text-red-400 hover:bg-red-100 transition-colors"
                                      >
                                        <Trash2 size={13} />
                                      </button>
                                    </div>
                                  </div>

                                  {/* Client info */}
                                  {slot.booking && (
                                    <div className="mt-2 pt-2 border-t border-white/30">
                                      <div className="flex items-center gap-1.5 mb-1">
                                        <User size={11} className="text-[#9e8476]" />
                                        <span className="text-xs font-medium text-[#3d2b1f]">
                                          {slot.booking.client_name}
                                        </span>
                                        {slot.booking.username && (
                                          <span className="text-[10px] text-[#9e8476]">
                                            @{slot.booking.username}
                                          </span>
                                        )}
                                      </div>
                                      {slot.booking.phone && (
                                        <div className="flex items-center gap-1.5">
                                          <Phone size={11} className="text-[#9e8476]" />
                                          <span className="text-xs text-[#7c5340]">
                                            {slot.booking.phone}
                                          </span>
                                        </div>
                                      )}
                                      {slot.booking.note && (
                                        <p className="text-[10px] text-[#9e8476] mt-1 italic">
                                          {slot.booking.note}
                                        </p>
                                      )}

                                      {/* Delete client button */}
                                      <button
                                        onClick={() =>
                                          setDeleteClientTarget({
                                            date: day.day_date,
                                            time: slot.time,
                                            clientName: slot.booking!.client_name,
                                          })
                                        }
                                        className="mt-2 flex items-center gap-1 text-[10px] text-red-400
                                          hover:text-red-600 transition-colors"
                                      >
                                        <XCircle size={11} />
                                        Удалить запись
                                      </button>
                                    </div>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Edit Client Modal ── */}
      <AnimatePresence>
        {editingClient && (
          <motion.div
            key="edit-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 overlay-backdrop"
            onClick={() => setEditingClient(null)}
          >
            <motion.div
              initial={{ opacity: 0, y: 60 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 40 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              className="liquid-glass rounded-3xl p-5 w-full max-w-sm"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-[#3d2b1f]">
                  {editingClient.isNew ? 'Добавить клиента' : 'Редактировать запись'}
                </h3>
                <button
                  onClick={() => setEditingClient(null)}
                  className="w-8 h-8 flex items-center justify-center rounded-xl liquid-glass-nav text-[#9e8476]"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-[#9e8476] mb-1 block">Слот</label>
                  <p className="text-sm font-medium text-[#3d2b1f]">
                    {formatDateRu(editingClient.date)} в {editingClient.time}
                  </p>
                </div>

                <div>
                  <label className="text-xs text-[#9e8476] mb-1.5 block">Имя клиента *</label>
                  <input
                    type="text"
                    value={editingClient.name}
                    onChange={(e) =>
                      setEditingClient((prev) => prev ? { ...prev, name: e.target.value } : null)
                    }
                    className="liquid-glass-input w-full px-3 py-2.5 rounded-xl text-[#3d2b1f] text-sm"
                    placeholder="Имя"
                  />
                </div>

                <div>
                  <label className="text-xs text-[#9e8476] mb-1.5 block">Телефон</label>
                  <input
                    type="tel"
                    value={editingClient.phone}
                    onChange={(e) =>
                      setEditingClient((prev) => prev ? { ...prev, phone: e.target.value } : null)
                    }
                    className="liquid-glass-input w-full px-3 py-2.5 rounded-xl text-[#3d2b1f] text-sm"
                    placeholder="+7 978 423-74-53"
                  />
                </div>

                <div>
                  <label className="text-xs text-[#9e8476] mb-1.5 block">Username Telegram</label>
                  <input
                    type="text"
                    value={editingClient.username || ''}
                    onChange={(e) =>
                      setEditingClient((prev) => prev ? { ...prev, username: e.target.value } : null)
                    }
                    className="liquid-glass-input w-full px-3 py-2.5 rounded-xl text-[#3d2b1f] text-sm"
                    placeholder="@username"
                  />
                </div>

                <div>
                  <label className="text-xs text-[#9e8476] mb-1.5 block">Заметка</label>
                  <textarea
                    value={editingClient.note || ''}
                    onChange={(e) =>
                      setEditingClient((prev) => prev ? { ...prev, note: e.target.value } : null)
                    }
                    rows={2}
                    className="liquid-glass-input w-full px-3 py-2.5 rounded-xl text-[#3d2b1f] text-sm resize-none"
                    placeholder="Доп. информация..."
                  />
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => setEditingClient(null)}
                    className="flex-1 py-2.5 rounded-xl liquid-glass-nav text-[#7c5340] text-sm font-medium"
                  >
                    Отмена
                  </button>
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={handleSaveClient}
                    disabled={isSaving || !editingClient.name.trim()}
                    className="flex-1 py-2.5 rounded-xl btn-primary text-sm font-medium
                      disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isSaving ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spinner" />
                    ) : (
                      <>
                        <Save size={14} />
                        Сохранить
                      </>
                    )}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Confirm Modals ── */}
      <ConfirmModal
        isOpen={!!deleteSlotTarget}
        title="Удалить слот?"
        message={`Вы уверены, что хотите удалить слот ${deleteSlotTarget?.time}?`}
        warning={deleteSlotTarget ? 'Если слот занят, запись также будет удалена' : undefined}
        confirmText="Удалить"
        onConfirm={handleDeleteSlot}
        onCancel={() => setDeleteSlotTarget(null)}
        danger
      />

      <ConfirmModal
        isOpen={!!deleteClientTarget}
        title="Удалить запись?"
        message={`Удалить запись клиента ${deleteClientTarget?.clientName || ''}?`}
        warning="Слот снова станет доступен для записи"
        confirmText="Удалить"
        onConfirm={handleDeleteClient}
        onCancel={() => setDeleteClientTarget(null)}
        danger
      />
    </div>
  );
}
