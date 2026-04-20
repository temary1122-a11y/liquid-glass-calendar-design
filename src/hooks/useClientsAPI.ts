// ============================================================
// src/hooks/useClientsAPI.ts — Хук для работы с API клиентов
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../config';

interface Client {
  id: number;
  name: string;
  phone: string;
  date: string;
  time: string;
  service: string;
  username?: string;
  userId?: string;
  note?: string;
  status: 'confirmed' | 'pending';
}

interface UseClientsAPIReturn {
  clients: Client[];
  isLoading: boolean;
  error: string | null;
  addClient: (client: Omit<Client, 'id'>) => Promise<void>;
  updateClient: (client: Client) => Promise<void>;
  deleteClient: (date: string, time: string) => Promise<void>;
  refreshClients: () => Promise<void>;
}

export function useClientsAPI(): UseClientsAPIReturn {
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const ADMIN_ID = import.meta.env.VITE_ADMIN_ID || '1834686956';

  // Загрузка клиентов с API
  const fetchClients = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Получаем все рабочие дни
      const workDaysResponse = await fetch(`${BACKEND_URL}/api/admin/work-days`, {
        headers: {
          'x-admin-id': ADMIN_ID,
        },
      });

      if (!workDaysResponse.ok) {
        throw new Error(`Failed to fetch work days: ${workDaysResponse.status}`);
      }

      const workDays = await workDaysResponse.json();

      // Загружаем клиентов для каждого дня
      const allClients: Client[] = [];
      for (const day of workDays) {
        const bookingsResponse = await fetch(`${BACKEND_URL}/api/admin/bookings/${day.date}`, {
          headers: {
            'x-admin-id': ADMIN_ID,
          },
        });

        if (bookingsResponse.ok) {
          const bookings = await bookingsResponse.json();
          for (const booking of bookings) {
            allClients.push({
              id: booking.id,
              name: booking.client_name,
              phone: booking.phone,
              date: booking.day_date,
              time: booking.slot_time,
              service: booking.service_id || 'Запись',
              username: booking.username,
              userId: booking.user_id ? String(booking.user_id) : undefined,
              note: booking.note,
              status: booking.status || 'confirmed',
            });
          }
        }
      }

      setClients(allClients);
    } catch (err) {
      console.error('Error fetching clients:', err);
      setError(err instanceof Error ? err.message : 'Failed to load clients');
    } finally {
      setIsLoading(false);
    }
  }, [ADMIN_ID]);

  // Добавление клиента через API
  const addClient = useCallback(async (client: Omit<Client, 'id'>) => {
    try {
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/create-client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
        },
        body: JSON.stringify({
          name: client.name,
          phone: client.phone,
          date: client.date,
          time: client.time,
          username: client.username,
          user_id: client.userId,
          note: client.note,
          status: client.status,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to add client');
      }

      const result = await response.json();
      
      // Обновляем локальное состояние
      setClients((prev) => [
        ...prev,
        {
          ...client,
          id: result.booking_id,
        },
      ]);
    } catch (err) {
      console.error('Error adding client:', err);
      setError(err instanceof Error ? err.message : 'Failed to add client');
      throw err;
    }
  }, [ADMIN_ID]);

  // Обновление клиента через API
  const updateClient = useCallback(async (client: Client) => {
    try {
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/update-client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
        },
        body: JSON.stringify({
          name: client.name,
          phone: client.phone,
          date: client.date,
          time: client.time,
          username: client.username,
          user_id: client.userId,
          note: client.note,
          status: client.status,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to update client');
      }

      // Обновляем локальное состояние
      setClients((prev) =>
        prev.map((c) => (c.id === client.id ? client : c))
      );
    } catch (err) {
      console.error('Error updating client:', err);
      setError(err instanceof Error ? err.message : 'Failed to update client');
      throw err;
    }
  }, [ADMIN_ID]);

  // Удаление клиента через API
  const deleteClient = useCallback(async (date: string, time: string) => {
    try {
      setError(null);

      const response = await fetch(`${BACKEND_URL}/api/admin/delete-client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-id': ADMIN_ID,
        },
        body: JSON.stringify({ date, time }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete client');
      }

      // Обновляем локальное состояние
      setClients((prev) =>
        prev.filter((c) => !(c.date === date && c.time === time))
      );
    } catch (err) {
      console.error('Error deleting client:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete client');
      throw err;
    }
  }, [ADMIN_ID]);

  // Перезагрузка клиентов
  const refreshClients = useCallback(async () => {
    await fetchClients();
  }, [fetchClients]);

  // Загружаем клиентов при монтировании
  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  return {
    clients,
    isLoading,
    error,
    addClient,
    updateClient,
    deleteClient,
    refreshClients,
  };
}
