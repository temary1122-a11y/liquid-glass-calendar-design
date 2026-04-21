import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Clock, Plus, Trash2, Edit3, Save, X } from 'lucide-react';
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
  }) => Promise<{ success: boolean; message?: string }>;
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
    note: ''
  });
  const [isSaving, setIsSaving] = useState(false);

  const slots = workDay?.slots || [];

  // Получаем клиента для конкретного слота
  const getClientForSlot = (time: string): AdminBooking | undefined => {
    return slots.find(s => s.time === time)?.booking;
  };

  // Открытие редактирования
  const handleEdit = (time: string) => {
    const client = getClientForSlot(time);
    if (client) {
      setEditForm({
        name: client.client_name,
        phone: client.phone,
        time: time,
        username: client.username || '',
        note: client.note || ''
      });
    } else {
      setEditForm({
        name: '',
        phone: '',
        time: time,
        username: '',
        note: ''
      });
    }
    setEditingSlot(time);
    vibrateLight();
  };

  // Сохранение изменений
  const handleSave = async () => {
    console.log('handleSave called, editingSlot:', editingSlot);
    console.log('editForm:', editForm);
    if (!editingSlot) return;

    setIsSaving(true);
    const dateStr = format(date, 'yyyy-MM-dd');
    const result = await onUpdateClient({
      name: editForm.name,
      phone: editForm.phone,
      date: dateStr,
      time: editForm.time,
      username: editForm.username || undefined,
      note: editForm.note || undefined
    });

    console.log('onUpdateClient result:', result);

    if (result.success) {
      vibrateSuccess();
      setEditingSlot(null);
      onRefresh();
    } else {
      vibrateError();
    }
    setIsSaving(false);
  };

  // Отмена редактирования
  const handleCancel = () => {
    setEditingSlot(null);
    setEditForm({ name: '', phone: '', time: '', username: '', note: '' });
    vibrateLight();
  };

  // Добавление слота
  const handleAddSlot = async (time: string) => {
    console.log('handleAddSlot called with:', time);
    const result = await onAddSlot(time);
    console.log('onAddSlot result:', result);

    if (result.success) {
      vibrateSuccess();
      setPickerOpen(false);
      setNewSlotTime('');
      onRefresh();
    } else {
      // Если рабочий день не найден, создаем его и повторяем
      if (result.message?.includes('не найден') || result.message?.includes('not found')) {
        console.log('Work day not found, creating it...');
        const dateStr = format(date, 'yyyy-MM-dd');
        const createResult = await onCreateWorkDay(dateStr);
        console.log('Create work day result:', createResult);

        if (createResult.success) {
          // Повторяем попытку добавления слота
          console.log('Retrying add slot...');
          const retryResult = await onAddSlot(time);
          console.log('Retry add slot result:', retryResult);

          if (retryResult.success) {
            vibrateSuccess();
            setPickerOpen(false);
            setNewSlotTime('');
            onRefresh();
          } else {
            vibrateError();
            console.error('Failed to add slot after creating work day:', retryResult.message);
          }
        } else {
          vibrateError();
          console.error('Failed to create work day:', createResult.message);
        }
      } else {
        vibrateError();
        console.error('Failed to add slot:', result.message);
      }
    }
  };

  // Удаление слота
  const handleDeleteSlot = async (time: string) => {
    const result = await onDeleteSlot(time);
    if (result.success) {
      vibrateSuccess();
      onRefresh();
    } else {
      vibrateError();
    }
  };

  // Удаление клиента
  const handleDeleteClient = async (time: string) => {
    const result = await onDeleteClient(time);
    if (result.success) {
      vibrateSuccess();
      onRefresh();
    } else {
      vibrateError();
    }
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
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.92 }}
          onClick={() => {
            vibrateMedium();
            setPickerOpen(v => !v);
            if (!pickerOpen) {
              setNewSlotTime('');
            }
          }}
          className="liquid-glass-nav h-9 px-4 rounded-xl flex items-center gap-1.5
            text-[#7c5340] text-xs font-semibold hover:text-[#3d2b1f] transition-colors"
        >
          <Plus size={13} strokeWidth={2.5} />
          <span>Слот</span>
        </motion.button>
      </div>

      {/* ── Time Picker (native) ── */}
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
                type="time"
                value={newSlotTime}
                onChange={(e) => setNewSlotTime(e.target.value)}
                className="liquid-glass-input flex-1 px-3 py-2 rounded-xl text-[#3d2b1f] text-sm"
              />
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={async () => {
                  if (newSlotTime) {
                    console.log('Adding slot:', newSlotTime);
                    const result = await handleAddSlot(newSlotTime);
                    console.log('Add slot result:', result);
                  }
                }}
                disabled={!newSlotTime}
                className="btn-primary px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
              >
                Добавить
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  setPickerOpen(false);
                  setNewSlotTime('');
                }}
                className="liquid-glass-nav px-4 py-2 rounded-xl text-sm font-medium text-[#7c5340]"
              >
                Отмена
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Slots list ── */}
      <div className="flex flex-col gap-2">
        {slots.length === 0 ? (
          <p className="text-center text-[#9e8476] text-xs py-4">
            Нет слотов — нажмите «+ Слот»
          </p>
        ) : (
          slots.sort((a, b) => a.time.localeCompare(b.time)).map((slot) => {
            const client = slot.booking;
            const isBooked = !!client;
            const isEditing = editingSlot === slot.time;

            return (
              <div key={slot.time} className="overflow-hidden">
                {isEditing ? (
                  <div className="liquid-glass p-3 rounded-xl space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      placeholder="Имя клиента"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <input
                      type="tel"
                      value={editForm.phone}
                      onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                      placeholder="Телефон"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <input
                      type="text"
                      value={editForm.username}
                      onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                      placeholder="@username (опционально)"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <input
                      type="text"
                      value={editForm.note}
                      onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                      placeholder="Заметка (опционально)"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-sm placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <div className="flex gap-2">
                      <button
                        onMouseDown={() => console.log('Save button onMouseDown, disabled:', isSaving || !editForm.name.trim(), 'name:', editForm.name)}
                        onClick={(e) => {
                          console.log('Save button onClick triggered');
                          e.stopPropagation();
                          handleSave();
                        }}
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
                  <div className={`liquid-glass p-3 rounded-xl flex items-center justify-between ${
                    isBooked ? 'bg-white/40 border border-[#c4967a]/20' : ''
                  }`}>

                    <div className="flex items-center gap-3 flex-1">
                      {isBooked ? (
                        <>
                          <div className="w-9 h-9 rounded-xl bg-[rgba(255,244,234,0.85)] border border-white/40
                            flex items-center justify-center text-xs font-semibold text-[#8b6049]">
                            {client.client_name[0]}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-[#3d2b1f] text-sm font-semibold leading-tight truncate">{client.client_name}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <p className="text-[#9e8476] text-xs">{slot.time}</p>
                              {client.username && (
                                <a
                                  href={`https://t.me/${client.username}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[#2e7d5e] text-[10px] font-medium hover:underline"
                                >
                                  @{client.username}
                                </a>
                              )}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="flex items-center gap-2 flex-1">
                          <Clock size={14} className="text-[#a07060]" />
                          <span className="text-[#3d2b1f] text-sm font-medium">{slot.time}</span>
                          <span className="text-[10px] text-[#9e8476]">Свободно</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {isBooked ? (
                        <>
                          <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => handleDeleteClient(slot.time)}
                            className="h-8 w-8 rounded-lg flex items-center justify-center text-[#ef4444] hover:bg-red-500/10 transition-colors"
                            title="Удалить запись"
                          >
                            <Trash2 size={12} />
                          </motion.button>
                        </>
                      ) : (
                        <>
                          <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => handleEdit(slot.time)}
                            className="h-8 w-8 rounded-lg flex items-center justify-center text-[#7c5340] hover:bg-white/20 transition-colors"
                            title="Добавить запись"
                          >
                            <Edit3 size={12} />
                          </motion.button>
                          <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => handleDeleteSlot(slot.time)}
                            className="h-8 w-8 rounded-lg flex items-center justify-center text-[#ef4444] hover:bg-red-500/10 transition-colors"
                            title="Удалить слот"
                          >
                            <Trash2 size={12} />
                          </motion.button>
                        </>
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
