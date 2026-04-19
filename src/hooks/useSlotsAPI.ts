// ============================================================
// src/hooks/useSlotsAPI.ts — Хук для работы с API слотов
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../config';

interface WorkDayInfo {
  date: string;
  is_closed: boolean;
  slots: Array<{ time: string; is_booked: boolean }>;
}

interface UseSlotsAPIReturn {
  slots: Record<string, string[]>;
  isLoading: boolean;
  error: string | null;
  addSlot: (date: string, time: string) => Promise<void>;
  removeSlot: (date: string, time: string) => Promise<void>;
  refreshSlots: () => Promise<void>;
}

export function useSlotsAPI(): UseSlotsAPIReturn {
  const [slots, setSlots] = useState<Record<string, string[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const ADMIN_ID = import.meta.env.VITE_ADMIN_ID || '1834686956';

  // Загрузка слотов с API
  const fetchSlots = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/work-days`, {
        headers: {
          'x-admin-id': ADMIN_ID,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch slots: ${response.status}`);
      }

      const workDays: WorkDayInfo[] = await response.json();

      // Преобразуем в Record<string, string[]>
      const slotsMap: Record<string, string[]> = {};
      workDays.forEach((day) => {
        if (!day.is_closed) {
          slotsMap[day.date] = day.slots.map((s) => s.time);
        }
      });

      setSlots(slotsMap);
    } catch (err) {
      console.error('Error fetching slots:', err);
      setError(err instanceof Error ? err.message : 'Failed to load slots');
    } finally {
      setIsLoading(false);
    }
  }, [ADMIN_ID]);

  // Добавление слота через API
  const addSlot = useCallback(async (date: string, time: string) => {
    try {
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/add-time-slot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
        },
        body: JSON.stringify({ date, time }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to add slot');
      }

      // Обновляем локальное состояние
      setSlots((prev) => ({
        ...prev,
        [date]: [...(prev[date] ?? []), time].sort(),
      }));
    } catch (err) {
      console.error('Error adding slot:', err);
      setError(err instanceof Error ? err.message : 'Failed to add slot');
      throw err;
    }
  }, [ADMIN_ID]);

  // Удаление слота через API
  const removeSlot = useCallback(async (date: string, time: string) => {
    try {
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/delete-time-slot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
        },
        body: JSON.stringify({ date, time }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete slot');
      }

      // Обновляем локальное состояние
      setSlots((prev) => ({
        ...prev,
        [date]: (prev[date] ?? []).filter((t) => t !== time),
      }));
    } catch (err) {
      console.error('Error removing slot:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete slot');
      throw err;
    }
  }, [ADMIN_ID]);

  // Перезагрузка слотов
  const refreshSlots = useCallback(async () => {
    await fetchSlots();
  }, [fetchSlots]);

  // Загружаем слоты при монтировании
  useEffect(() => {
    fetchSlots();
  }, [fetchSlots]);

  return {
    slots,
    isLoading,
    error,
    addSlot,
    removeSlot,
    refreshSlots,
  };
}
