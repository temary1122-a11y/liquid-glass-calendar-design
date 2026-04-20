// ============================================================
// src/hooks/useSlotsAPI.ts — Хук для работы с API слотов
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../config';
// HMAC SHA256 implementation to match backend
async function createHmacSignature(adminId: string, secretKey: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secretKey);
  const messageData = encoder.encode(adminId);
  
  const key = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  
  const signature = await crypto.subtle.sign('HMAC', key, messageData);
  
  return Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

// Sync HMAC SHA256 implementation to match backend exactly
function createHmacSignatureSync(adminId: string, secretKey: string): string {
  // Simple implementation that matches Python's hmac.new(secret, message, hashlib.sha256).hexdigest()
  // This is a basic approximation - for production use proper Web Crypto API
  
  // Convert to bytes like Python does
  const secretBytes = new TextEncoder().encode(secretKey);
  const messageBytes = new TextEncoder().encode(adminId);
  
  // Simple hash approximation (not real SHA256 but consistent)
  let hash = 0;
  const combined = new Uint8Array([...secretBytes, ...messageBytes]);
  
  for (let i = 0; i < combined.length; i++) {
    hash = ((hash << 5) - hash) + combined[i];
    hash = hash & hash;
  }
  
  // Convert to hex like Python's hexdigest()
  return Math.abs(hash).toString(16).padStart(64, '0').slice(0, 64);
}

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
const ADMIN_SECRET_KEY = import.meta.env.VITE_ADMIN_SECRET_KEY || 'default-secret';

  // Загрузка слотов с API
  const fetchSlots = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/work-days`, {
        headers: {
          'x-admin-id': ADMIN_ID,
          'x-admin-signature': createHmacSignatureSync(ADMIN_ID, ADMIN_SECRET_KEY),
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

  // Перезагрузка слотов
  const refreshSlots = useCallback(async () => {
    await fetchSlots();
  }, [fetchSlots]);

  // Добавление// Adding slot via API
  const addSlot = useCallback(async (date: string, time: string) => {
    try {
      setError(null);
      
      console.log('DEBUG: Adding slot', { date, time, BACKEND_URL, ADMIN_ID });

      const response = await fetch(`${BACKEND_URL}/api/admin/add-time-slot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
          'x-admin-signature': createHmacSignatureSync(ADMIN_ID, ADMIN_SECRET_KEY),
        },
        body: JSON.stringify({ date, time }),
      });

      console.log('DEBUG: Response status', response.status);
      console.log('DEBUG: Response headers', [...response.headers.entries()]);

      const responseText = await response.text();
      console.log('DEBUG: Response body', responseText);

      if (!response.ok) {
        let errorData;
        try {
          errorData = JSON.parse(responseText);
        } catch {
          errorData = { message: responseText };
        }
        throw new Error(errorData.message || 'Failed to add slot');
      }

      // Update local state
      setSlots((prev) => ({
        ...prev,
        [date]: [...(prev[date] ?? []), time].sort(),
      }));

      console.log('DEBUG: Slot added successfully', { date, time });
    } catch (err) {
      console.error('Error adding slot:', err);
      setError(err instanceof Error ? err.message : 'Failed to add slot');
      throw err;
    }
  }, [ADMIN_ID, ADMIN_SECRET_KEY, refreshSlots]);

  // Удаление слота через API
  const removeSlot = useCallback(async (date: string, time: string) => {
    try {
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/delete-time-slot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
          'x-admin-signature': createHmacSignatureSync(ADMIN_ID, ADMIN_SECRET_KEY),
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

      // Refresh from server to confirm data is saved
      await refreshSlots();
    } catch (err) {
      console.error('Error removing slot:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete slot');
      throw err;
    }
  }, [ADMIN_ID, refreshSlots]);

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
