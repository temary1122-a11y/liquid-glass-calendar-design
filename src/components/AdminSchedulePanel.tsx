import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isToday,
  isBefore,
  startOfDay,
  parseISO,
} from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Users,
  Clock,
  Plus,
  Trash2,
} from 'lucide-react';
import { useSwipeable } from 'react-swipeable';
import { MOCK_CLIENTS } from '../mockData';
import { useVibration, VIBRATION_PATTERNS } from '../hooks/useVibration';
import { useSlotsAPI } from '../hooks/useSlotsAPI';
import { useClientsAPI } from '../hooks/useClientsAPI';
import TimePicker from './TimePicker';

const DAYS_HEADER = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getMonthDays(month: Date): Date[] {
  const start = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
  const end   = endOfWeek(endOfMonth(month),   { weekStartsOn: 1 });
  return eachDayOfInterval({ start, end });
}

// ─── Nav button ───────────────────────────────────────────────────────────────
function NavButton({ onClick, direction }: { onClick: () => void; direction: 'left' | 'right' }) {
  return (
    <motion.button
      whileTap={{ scale: 0.90 }}
      onClick={onClick}
      className="liquid-glass-nav w-11 h-11 flex items-center justify-center rounded-2xl
        text-[#a07060] hover:text-[#7c5340] transition-colors duration-200"
    >
      {direction === 'left'
        ? <ChevronLeft size={18} strokeWidth={2.5} />
        : <ChevronRight size={18} strokeWidth={2.5} />
      }
    </motion.button>
  );
}

// ─── Admin DayCard ────────────────────────────────────────────────────────────
interface AdminDayCardProps {
  date: Date;
  slots: string[];
  isCurrentMonth: boolean;
  isSelected: boolean;
  onClick: () => void;
  bookedClients?: Array<{ time: string; status?: 'pending' | 'confirmed' }>; // Клиенты с информацией о статусах
}

function AdminDayCard({ date, slots, isCurrentMonth, isSelected, onClick, bookedClients = [] }: AdminDayCardProps) {
  const isPast     = isBefore(startOfDay(date), startOfDay(new Date()));
  const isToday_   = isToday(date);
  const hasSlots   = slots.length > 0;
  const { vibrate } = useVibration();

  const handleClick = () => {
    vibrate(VIBRATION_PATTERNS.TAP);
    onClick();
  };

  if (!isCurrentMonth) return <div className="min-h-[64px] rounded-3xl" />;

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.94 }}
      onClick={handleClick}
      className={`
        relative rounded-3xl p-2 min-h-[64px] w-full text-left
        liquid-glass-calendar transition-all duration-200
        ${isPast ? 'opacity-40' : ''}
        ${isSelected ? 'ring-2 ring-[#7c5340]/50 bg-white/20' : ''}
        ${isToday_ && !isSelected ? 'ring-1 ring-[#2e7d5e]/40' : ''}
      `}
    >
      {/* Glass highlight */}
      <div className="glass-highlight absolute inset-x-0 top-0 h-[45%] rounded-t-3xl pointer-events-none z-10" />

      {/* Day number - фиксированная позиция наверху */}
      <span className={`
        absolute top-2 left-2 z-20 text-[11px] font-semibold leading-none
        ${isToday_ ? 'text-[#2e7d5e]' : 'text-[#3d2b1f]'}
      `}>
        {format(date, 'd')}
      </span>

      {/* Slot count badge - показываем все точки без "+N" */}
      {hasSlots && !isPast && (
        <div className="relative z-20 flex flex-wrap gap-0.5 mt-4">
          {slots.map((slot) => {
            const client = bookedClients.find(c => c.time === slot);
            const isBooked = !!client;
            const status = client?.status;

            return (
              <span
                key={slot}
                className={`
                  w-1.5 h-1.5 rounded-full inline-block
                  ${!isBooked
                    ? 'bg-[#a07060]/60' // Коричневый для свободных
                    : status === 'pending'
                      ? 'bg-[#ef4444]' // Красный для ожидающих
                      : 'bg-[#2e7d5e]' // Зелёный для подтверждённых
                  }
                `}
              />
            );
          })}
        </div>
      )}
    </motion.button>
  );
}

// ─── SelectedDayPanel ─────────────────────────────────────────────────────────
interface SelectedDayPanelProps {
  date: Date;
  slots: string[];
  onAddSlot: (time: string) => void;
  onRemoveSlot: (time: string) => void;
  bookedClients?: Array<{ name: string; time: string; userId?: string; username?: string; note?: string; status?: 'pending' | 'confirmed' }>;
  onUpdateClient?: (oldTime: string, newClient: { name: string; time: string; userId?: string; username?: string; note?: string }, isNewClient: boolean) => void;
}

function SelectedDayPanel({ date, slots, onAddSlot, onRemoveSlot, bookedClients = [], onUpdateClient }: SelectedDayPanelProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [editTimePickerOpen, setEditTimePickerOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    time: '',
    username: '',
    userId: '',
    note: ''
  });
  const [pickerTime, setPickerTime] = useState('09:00'); // Local state for picker
  const { vibrate } = useVibration();

  // Получаем клиента для конкретного слота
  const getClientForSlot = (time: string) => {
    return bookedClients.find(client => client.time === time);
  };

  // Открытие редактирования
  const handleEdit = (time: string) => {
    const client = getClientForSlot(time);
    if (client) {
      // Редактирование существующего клиента
      setEditForm({
        name: client.name,
        time: client.time,
        username: client.username || '',
        userId: client.userId || '',
        note: client.note || ''
      });
    } else {
      // Создание нового клиента для пустого слота
      setEditForm({
        name: '',
        time: time,
        username: '',
        userId: '',
        note: ''
      });
    }
    setEditingSlot(time);
  };

  // Сохранение изменений
  const handleSave = () => {
    if (editingSlot && onUpdateClient) {
      const existingClient = getClientForSlot(editingSlot);
      const isNewClient = !existingClient;

      onUpdateClient(editingSlot, {
        name: editForm.name,
        time: editForm.time,
        username: editForm.username || undefined,
        userId: editForm.userId || undefined,
        note: editForm.note || undefined
      }, isNewClient);
      vibrate(VIBRATION_PATTERNS.SUCCESS);
    }
    setEditingSlot(null);
  };

  // Отмена редактирования
  const handleCancel = () => {
    setEditingSlot(null);
    setEditForm({ name: '', time: '', username: '', userId: '', note: '' });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className="liquid-glass-admin p-4 mt-3"
    >
      {/* ── Panel header ── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock size={15} className="text-[#a07060]" />
          <span className="text-[#3d2b1f] text-sm font-semibold capitalize">
            {format(date, 'd MMMM', { locale: ru })}
          </span>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.92 }}
          onClick={() => {
            vibrate(VIBRATION_PATTERNS.LIGHT);
            setPickerTime('09:00'); // Reset to default time
            setPickerOpen(v => !v);
          }}
          className="liquid-glass-nav h-9 px-4 rounded-xl flex items-center gap-1.5
            text-[#7c5340] text-xs font-semibold hover:text-[#3d2b1f] transition-colors"
        >
          <Plus size={13} strokeWidth={2.5} />
          <span>Слот</span>
        </motion.button>
      </div>

      {/* ── Time Picker (iOS-style) ── */}
      <TimePicker
        open={pickerOpen}
        value={pickerTime}
        onChange={(time) => {
          setPickerTime(time); // Update picker time with live preview
        }}
        onConfirm={() => {
          onAddSlot(pickerTime); // Use the current picker time
        }}
        onClose={() => setPickerOpen(false)}
      />

      {/* ── Slots list ── */}
      <div className="flex flex-col gap-1.5">
        {slots.length === 0 ? (
          <p className="text-center text-[#9e8476] text-xs py-3">
            Нет слотов — нажмите «+ Слот»
          </p>
        ) : (
          slots.sort().map(time => {
            const client = getClientForSlot(time);
            const isBooked = !!client;
            const isEditing = editingSlot === time;

            return (
              <AnimatePresence mode="wait" key={time}>
                {isEditing ? (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    className="liquid-glass-slot p-3 rounded-xl space-y-2"
                  >
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      placeholder="Имя клиента"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-base placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => setEditTimePickerOpen(true)}
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-base focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50 text-left"
                    >
                      {editForm.time || 'Выберите время'}
                    </motion.button>
                    <input
                      type="text"
                      value={editForm.username}
                      onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                      placeholder="@username (опционально)"
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-base placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50"
                    />
                    <textarea
                      value={editForm.note}
                      onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                      placeholder="Примечание (запись через телефон и т.д.)"
                      rows={2}
                      className="w-full px-3 py-2 rounded-lg bg-white/50 border border-white/40 text-[#3d2b1f] text-base placeholder-[#9e8476] focus:outline-none focus:ring-2 focus:ring-[#c4967a]/50 resize-none"
                    />
                    <div className="flex gap-2">
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.92 }}
                        onClick={handleSave}
                        className="small-touch flex-1 h-9 px-4 rounded-xl bg-[#2e7d5e] text-white text-xs font-semibold hover:bg-[#2e7d5e]/80 transition-colors"
                      >
                        Сохранить
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.92 }}
                        onClick={handleCancel}
                        className="small-touch flex-1 h-9 px-4 rounded-xl bg-[#c4967a]/20 text-[#c4967a] text-xs font-semibold hover:bg-[#c4967a]/30 transition-colors"
                      >
                        Отмена
                      </motion.button>
                    </div>
                    
                    {/* TimePicker для редактирования */}
                    <TimePicker
                      open={editTimePickerOpen}
                      value={editForm.time}
                      onChange={(time) => {
                        setEditForm({ ...editForm, time }); // Только обновляем состояние
                      }}
                      onConfirm={() => {
                        vibrate(VIBRATION_PATTERNS.SUCCESS);
                        setEditTimePickerOpen(false);
                      }}
                      onClose={() => setEditTimePickerOpen(false)}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key={time}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    onClick={() => handleEdit(time)}
                    className={`
                      h-11 flex items-center justify-between px-3 rounded-xl cursor-pointer
                      ${isBooked
                        ? client.status === 'pending'
                          ? 'liquid-glass-slot bg-[#ef4444]/10 border border-[#ef4444]/30'
                          : 'liquid-glass-slot bg-[#2e7d5e]/10 border border-[#2e7d5e]/30'
                        : 'liquid-glass-slot'
                      }
                    `}
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <span className="text-[#8b6049] text-sm font-semibold leading-4">{time}</span>
                      {isBooked && (
                        <>
                          <span className="text-[#9e8476] leading-4">•</span>
                          <span className="text-[#3d2b1f] text-xs font-medium leading-4">{client.name}</span>
                          {(client.username || client.userId) && (
                            <a
                              onClick={(e: React.MouseEvent) => e.stopPropagation()}
                              href={client.username ? `https://t.me/${client.username}` : `https://t.me/user?id=${client.userId}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#2e7d5e] text-xs font-medium hover:underline leading-4 inline-flex items-center"
                            >
                              @{client.username || client.userId}
                            </a>
                          )}
                        </>
                      )}
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.1, backgroundColor: 'rgba(239, 68, 68, 0.1)' }}
                      whileTap={{ scale: 0.9 }}
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        vibrate(VIBRATION_PATTERNS.DELETE);
                        onRemoveSlot(time);
                      }}
                      className="small-touch w-8 h-8 flex items-center justify-center rounded-lg
                        text-[#c4967a] hover:text-red-400 hover:bg-red-50/30
                        transition-all duration-200 flex-shrink-0"
                      title="Удалить слот"
                    >
                      <Trash2 size={14} strokeWidth={2} />
                    </motion.button>
                  </motion.div>
                )}
              </AnimatePresence>
            );
          })
        )}
      </div>
    </motion.div>
  );
}

// ─── Clients Tab ──────────────────────────────────────────────────────────────
function ClientsTab({ clients, onConfirmBooking }: { clients: typeof MOCK_CLIENTS; onConfirmBooking: (clientId: number) => void }) {
  const [clientsSubTab, setClientsSubTab] = useState<'all' | 'pending'>('all');
  const pendingClients = clients.filter(c => c.status === 'pending');
  const { vibrate } = useVibration();

  return (
    <div className="flex flex-col gap-2 mt-1">
      {/* Sub-tab switcher */}
      <div className="liquid-glass-tab rounded-full p-1.5 flex relative mb-3">
        <AnimatePresence mode="wait">
          {pendingClients.length > 0 && (
            <>
              <motion.button
                key="all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  vibrate(VIBRATION_PATTERNS.MEDIUM);
                  setClientsSubTab('all');
                }}
                className={`
                  flex-1 h-8 rounded-full text-[11px] font-semibold transition-all duration-200 relative z-10
                  ${clientsSubTab === 'all' ? 'text-[#3d2b1f]' : 'text-[#9e8476] hover:text-[#7c5340]'}
                `}
              >
                Все клиенты
              </motion.button>
              <motion.button
                key="pending"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  vibrate(VIBRATION_PATTERNS.MEDIUM);
                  setClientsSubTab('pending');
                }}
                className={`
                  flex-1 h-8 rounded-full text-[11px] font-semibold transition-all duration-200 relative z-10
                  ${clientsSubTab === 'pending' ? 'text-[#3d2b1f]' : 'text-[#9e8476] hover:text-[#7c5340]'}
                `}
              >
                Ожидающие ({pendingClients.length})
              </motion.button>
              <motion.div
                layoutId="clientsTabBg"
                className="absolute inset-1.5 bg-white/40 rounded-full"
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                style={{
                  left: clientsSubTab === 'all' ? '0%' : '50%',
                  right: clientsSubTab === 'all' ? '50%' : '0%',
                }}
              />
            </>
          )}
        </AnimatePresence>
      </div>

      {/* Clients list */}
      <div className="flex flex-col gap-2">
        {(clientsSubTab === 'pending' ? pendingClients : clients).map((client, index) => (
          <motion.div
            key={client.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{ scale: 1.01, backgroundColor: 'rgba(255, 255, 255, 0.12)' }}
            className={`liquid-glass-admin p-3 flex items-center justify-between rounded-xl ${
              client.status === 'pending' ? 'border-l-4 border-l-[#ef4444]' : ''
            }`}
          >
            <div className="flex items-center gap-3 flex-1">
              {/* Avatar */}
              <div className="w-10 h-10 rounded-2xl bg-[rgba(255,244,234,0.85)] border border-white/40
                flex items-center justify-center text-sm font-semibold text-[#8b6049]">
                {client.name[0]}
              </div>
              <div className="flex-1">
                <p className="text-[#3d2b1f] text-sm font-semibold leading-tight">{client.name}</p>
                <p className="text-[#9e8476] text-[11px] mt-0.5">{client.service}</p>
                {(client.username || client.userId) && (
                  <motion.a
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => vibrate(VIBRATION_PATTERNS.LIGHT)}
                    href={client.username ? `https://t.me/${client.username}` : `https://t.me/user?id=${client.userId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#2e7d5e] text-[10px] font-medium hover:underline mt-0.5 inline-block"
                  >
                    @{client.username || client.userId}
                  </motion.a>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-[#7c5340] text-xs font-semibold">{client.time}</p>
                <p className="text-[#9e8476] text-[10px] mt-0.5">
                  {format(parseISO(client.date), 'd MMM', { locale: ru })}
                </p>
              </div>
              {client.status === 'pending' && (
                <motion.button
                  whileHover={{ scale: 1.05, backgroundColor: 'rgba(46, 125, 94, 0.9)' }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => {
                    vibrate(VIBRATION_PATTERNS.IMPORTANT);
                    onConfirmBooking(client.id);
                  }}
                  className="h-8 px-3 rounded-xl bg-[#2e7d5e] text-white text-[10px] font-semibold hover:bg-[#2e7d5e]/80 transition-colors"
                >
                  Подтвердить
                </motion.button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ─── Main AdminSchedulePanel ──────────────────────────────────────────────────
export default function AdminSchedulePanel() {
  const [activeTab, setActiveTab]   = useState<'calendar' | 'clients'>('calendar');
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDay, setSelectedDay]   = useState<string | null>(format(new Date(), 'yyyy-MM-dd'));
  const { slots, addSlot, removeSlot, error: slotsError } = useSlotsAPI();
  const { clients, addClient: addClientAPI, updateClient: updateClientAPI } = useClientsAPI();
  const { vibrate } = useVibration();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const days = getMonthDays(currentMonth);

  const prevMonth = useCallback(() => {
    vibrate(VIBRATION_PATTERNS.LIGHT);
    setCurrentMonth(m => new Date(m.getFullYear(), m.getMonth() - 1, 1));
  }, [vibrate]);

  const nextMonth = useCallback(() => {
    vibrate(VIBRATION_PATTERNS.LIGHT);
    setCurrentMonth(m => new Date(m.getFullYear(), m.getMonth() + 1, 1));
  }, [vibrate]);

  const swipeHandlers = useSwipeable({
    onSwipedLeft:  nextMonth,
    onSwipedRight: prevMonth,
    trackTouch: true,
    delta: 50,
  });

  const updateClient = async (oldTime: string, newClient: { name: string; time: string; userId?: string; username?: string; note?: string }, isNewClient: boolean) => {
    const dateKey = selectedDay;
    if (!dateKey) return;

    if (isNewClient) {
      // Создание нового клиента через API
      const hasTelegram = !!(newClient.username || newClient.userId);
      await addClientAPI({
        name: newClient.name,
        phone: '', // Будет заполнено в форме
        date: dateKey,
        time: newClient.time,
        service: 'Запись',
        username: newClient.username,
        userId: newClient.userId,
        note: newClient.note,
        status: hasTelegram ? 'pending' : 'confirmed',
      });
    } else {
      // Обновление существующего клиента через API
      const existingClient = clients.find(c => c.date === dateKey && c.time === oldTime);
      if (existingClient) {
        await updateClientAPI({
          ...existingClient,
          name: newClient.name,
          time: newClient.time,
          username: newClient.username,
          userId: newClient.userId || existingClient.userId,
          note: newClient.note,
        });
      }
    }
  };

  const confirmBooking = async (clientId: number) => {
    const client = clients.find(c => c.id === clientId);
    if (!client) return;

    // Проверяем наличие username или userId
    if (!client.username && !client.userId) {
      console.error('Нет username или userId для отправки сообщения');
      return;
    }

    // Обновляем статус через API
    await updateClientAPI({
      ...client,
      status: 'confirmed',
    });
  };

  const selectedDate = selectedDay ? parseISO(selectedDay) : null;
  const selectedSlots = selectedDay ? (slots[selectedDay] ?? []) : [];

  const getClientsForDate = (date: Date): typeof MOCK_CLIENTS => {
    const key = format(date, 'yyyy-MM-dd');
    return clients.filter((client: typeof MOCK_CLIENTS[0]) => client.date === key);
  };

  return (
    <div className="liquid-glass-admin p-4 w-full">

      {/* Mobile Messages */}
      <AnimatePresence>
        {slotsError && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-800 text-xs mb-4"
          >
            <div className="font-semibold">ERROR:</div>
            <div className="mt-1">{slotsError}</div>
            <div className="mt-2 text-red-600">
              Backend: {import.meta.env.VITE_BACKEND_URL || 'https://liquid-glass-calendar-design.onrender.com'}
            </div>
          </motion.div>
        )}

        {successMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-green-50 border border-green-200 rounded-xl p-3 text-green-800 text-xs mb-4"
          >
            <div className="font-semibold">SUCCESS:</div>
            <div className="mt-1">{successMessage}</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[#3d2b1f] font-semibold text-base">
          Панель мастера
        </h2>
      </div>

      {/* ── Tab switcher ── */}
      <div className="liquid-glass-tab rounded-full p-1.5 flex relative mb-4">
        {/* Sliding indicator */}
        <motion.div
          layout
          className="absolute top-1.5 bottom-1.5 w-[calc(50%-6px)] rounded-full bg-white shadow-sm"
          animate={{ left: activeTab === 'calendar' ? '6px' : 'calc(50% + 3px)' }}
          transition={{ type: 'spring', stiffness: 380, damping: 34 }}
        />

        {(['calendar', 'clients'] as const).map(tab => (
          <motion.button
            key={tab}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              vibrate(VIBRATION_PATTERNS.MEDIUM);
              setActiveTab(tab);
            }}
            className={`
              flex-1 h-11 rounded-full flex items-center justify-center gap-2 relative z-10
              text-sm font-medium transition-colors duration-300
              ${activeTab === tab ? 'text-[#3d2b1f]' : 'text-[#9e8476] hover:text-[#3d2b1f]'}
            `}
          >
            {tab === 'calendar'
              ? <><CalendarIcon size={16} /><span>Календарь</span></>
              : <><Users size={16} /><span>Клиенты</span></>
            }
          </motion.button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <AnimatePresence mode="wait">
        {activeTab === 'calendar' ? (
          <motion.div
            key="calendar"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.20 }}
          >
            {/* Admin calendar grid */}
            <div className="liquid-glass-calendar p-3" {...swipeHandlers}>
              {/* Month navigation */}
              <div className="flex items-center justify-between mb-3">
                <NavButton direction="left" onClick={prevMonth} />
                <motion.span
                  key={format(currentMonth, 'yyyy-MM')}
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-[#3d2b1f] font-semibold text-sm capitalize"
                >
                  {format(currentMonth, 'LLLL yyyy', { locale: ru })}
                </motion.span>
                <NavButton direction="right" onClick={nextMonth} />
              </div>

              {/* Days of week */}
              <div className="grid grid-cols-7 mb-1.5">
                {DAYS_HEADER.map(d => (
                  <div key={d} className="flex items-center justify-center">
                    <span className="text-[10px] font-semibold text-[#9e8476] uppercase tracking-widest">
                      {d}
                    </span>
                  </div>
                ))}
              </div>

              {/* Days grid */}
              <div className="grid grid-cols-7 gap-1">
                {days.map(date => {
                  const key = format(date, 'yyyy-MM-dd');
                  const clientsForDate = getClientsForDate(date);

                  return (
                    <AdminDayCard
                      key={key}
                      date={date}
                      slots={slots[key] ?? []}
                      isCurrentMonth={isSameMonth(date, currentMonth)}
                      isSelected={selectedDay === key}
                      onClick={() => setSelectedDay(prev => prev === key ? null : key)}
                      bookedClients={clientsForDate.map(c => ({ time: c.time, status: c.status }))}
                    />
                  );
                })}
              </div>
            </div>

            {/* Selected day panel */}
            <AnimatePresence>
              {selectedDay && selectedDate && (
                <SelectedDayPanel
                  date={selectedDate}
                  slots={selectedSlots}
                  onAddSlot={time => addSlot(selectedDay, time)}
                  onRemoveSlot={time => removeSlot(selectedDay, time)}
                  bookedClients={getClientsForDate(selectedDate)}
                  onUpdateClient={updateClient}
                />
              )}
            </AnimatePresence>
          </motion.div>
        ) : (
          <motion.div
            key="clients"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.20 }}
          >
            <ClientsTab clients={clients} onConfirmBooking={confirmBooking} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
