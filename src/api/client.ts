// ============================================================
// src/api/client.ts — HTTP клиент для работы с backend API
// ============================================================

import { BACKEND_URL, BOT_CONFIG, ADMIN_SECRET_KEY } from '../config';

// Simple pseudo-HMAC for admin auth (matches backend)
function createAdminSignature(adminId: string): string {
  const secretBytes = new TextEncoder().encode(ADMIN_SECRET_KEY);
  const messageBytes = new TextEncoder().encode(adminId);
  let hash = 0;
  const combined = new Uint8Array([...secretBytes, ...messageBytes]);
  for (let i = 0; i < combined.length; i++) {
    hash = ((hash << 5) - hash) + combined[i];
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16).padStart(64, '0').slice(0, 64);
}

function getAdminHeaders(): Record<string, string> {
  const adminId = BOT_CONFIG.ADMIN_ID;
  return {
    'Content-Type': 'application/json',
    'x-admin-id': adminId,
    'x-admin-signature': createAdminSignature(adminId),
  };
}

function getUserInitData(): string {
  return window.Telegram?.WebApp?.initData || '';
}

// ─── Types ───────────────────────────────────────────────────

export interface TimeSlot {
  time: string;
  available: boolean;
}

export interface WorkDay {
  date: string;
  slots: TimeSlot[];
  is_closed: boolean;
}

export interface BookingRequest {
  name: string;
  phone?: string;
  date: string;
  time: string;
  service_id?: string;
  user_id?: number;
  username?: string;
}

export interface BookingResponse {
  success: boolean;
  message: string;
  booking_id?: number;
}

export interface UserBooking {
  id: number;
  client_name: string;
  phone?: string;
  day_date: string;
  slot_time: string;
  status: 'pending' | 'confirmed' | 'cancelled' | 'completed';
  is_cancelled: boolean;
  cancel_reason?: string;
  created_at: string;
  cancelled_at?: string;
}

export interface AdminWorkDay {
  day_date: string;
  is_closed: boolean;
  slots: AdminSlot[];
}

export interface AdminSlot {
  time: string;
  is_booked: boolean;
  booking?: AdminBooking;
}

export interface AdminBooking {
  id: number;
  client_name: string;
  phone: string;
  username?: string;
  user_id?: number;
  note?: string;
  status: string;
}

// ─── API Client ──────────────────────────────────────────────

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  // ── Client endpoints ──────────────────────────────────────

  async getAvailableDates(): Promise<WorkDay[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/booking/available-dates`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('getAvailableDates error:', e);
      return [];
    }
  }

  async createBooking(data: BookingRequest): Promise<BookingResponse> {
    try {
      const res = await fetch(`${this.baseUrl}/api/booking/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
        return { success: false, message: err.message || 'Ошибка сервера' };
      }
      return await res.json();
    } catch (e) {
      console.error('createBooking error:', e);
      return { success: false, message: 'Ошибка соединения с сервером' };
    }
  }

  async getUserBookings(userId: number): Promise<UserBooking[]> {
    try {
      const initData = getUserInitData();
      const res = await fetch(
        `${this.baseUrl}/api/profile/bookings?user_id=${userId}`,
        {
          headers: {
            'Content-Type': 'application/json',
            ...(initData ? { 'x-init-data': initData } : {}),
          },
        }
      );
      if (!res.ok) return [];
      return await res.json();
    } catch (e) {
      console.error('getUserBookings error:', e);
      return [];
    }
  }

  async cancelBookingByUser(
    bookingId: number,
    reason: string,
    userId: number
  ): Promise<{ success: boolean; message: string }> {
    try {
      const initData = getUserInitData();
      const res = await fetch(`${this.baseUrl}/api/profile/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(initData ? { 'x-init-data': initData } : {}),
        },
        body: JSON.stringify({ booking_id: bookingId, reason, user_id: userId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ message: 'Ошибка' }));
        return { success: false, message: err.message };
      }
      return await res.json();
    } catch (e) {
      console.error('cancelBookingByUser error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }

  // ── Admin endpoints ──────────────────────────────────────

  async getWorkDaysWithBookings(): Promise<Record<string, AdminWorkDay>> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/work-days-with-bookings`, {
        headers: getAdminHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('getWorkDaysWithBookings error:', e);
      return {};
    }
  }

  async getArchive(): Promise<UserBooking[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/archive`, {
        headers: getAdminHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('getArchive error:', e);
      return [];
    }
  }

  async addTimeSlot(
    date: string,
    time: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/add-time-slot`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify({ date, time }),
      });
      return await res.json();
    } catch (e) {
      console.error('addTimeSlot error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }

  async deleteTimeSlot(
    date: string,
    time: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/delete-time-slot`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify({ date, time }),
      });
      return await res.json();
    } catch (e) {
      console.error('deleteTimeSlot error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }

  async createClient(data: {
    name: string;
    phone: string;
    date: string;
    time: string;
    username?: string;
    user_id?: number;
    note?: string;
  }): Promise<{ success: boolean; message: string; booking_id?: number }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/create-client`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify(data),
      });
      return await res.json();
    } catch (e) {
      console.error('createClient error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }

  async updateClient(data: {
    name: string;
    phone: string;
    date: string;
    time: string;
    username?: string;
    note?: string;
    status?: string;
  }): Promise<{ success: boolean; message: string; data?: { type: string; user_id: number; text: string } }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/update-client`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify(data),
      });
      return await res.json();
    } catch (e) {
      console.error('updateClient error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }

  async deleteClient(
    date: string,
    time: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/delete-client`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify({ date, time }),
      });
      return await res.json();
    } catch (e) {
      console.error('deleteClient error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }

  async notifyCancellation(data: {
    client_name: string;
    slot_time: string;
    day_date: string;
    reason?: string;
  }): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/api/admin/notify-cancellation`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify(data),
      });
    } catch (e) {
      console.error('notifyCancellation error:', e);
    }
  }

  async addWorkDay(
    date: string,
    slots?: string[]
  ): Promise<{ success: boolean; message?: string }> {
    try {
      const res = await fetch(`${this.baseUrl}/api/admin/add-work-day`, {
        method: 'POST',
        headers: getAdminHeaders(),
        body: JSON.stringify({ date, time_slots: slots }),
      });
      return await res.json();
    } catch (e) {
      console.error('addWorkDay error:', e);
      return { success: false, message: 'Ошибка соединения' };
    }
  }
}

export const apiClient = new ApiClient(BACKEND_URL);
