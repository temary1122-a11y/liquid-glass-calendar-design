// ============================================================
// src/api/client.ts — API клиент для Liquid Glass Calendar Design
// ============================================================

class ApiClient {
  private baseUrl: string;

  constructor() {
    // Используем BASE_URL из env или дефолтное значение (Render URL)
    this.baseUrl = import.meta.env.VITE_BACKEND_URL || 'https://liquid-glass-calendar-design.onrender.com';
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseUrl}${endpoint}`;

    console.group(`API Request: ${options.method || 'GET'} ${endpoint}`);
    console.log('URL:', url);
    console.log('Options:', options);

    if (options.body) {
      console.log('Body (string):', options.body);
      try {
        console.log('Body (parsed):', JSON.parse(options.body as string));
      } catch (e) {
        console.error('Body is not valid JSON!');
      }
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      const data = await response.json();
      console.log('Response data:', data);
      console.groupEnd();

      if (!response.ok) {
        throw new Error((data as any).detail || `HTTP ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('Request failed:', error);
      console.groupEnd();
      throw error;
    }
  }

  // Booking endpoints
  async getAvailableDates() {
    return this.request('/api/booking/available-dates');
  }

  async createBooking(bookingData: any) {
    return this.request('/api/booking/book', {
      method: 'POST',
      body: JSON.stringify(bookingData),
    });
  }

  async getMyBookings(userId: string) {
    return this.request(`/api/booking/my-bookings/${userId}`);
  }

  async cancelBooking(bookingId: string) {
    return this.request(`/api/booking/cancel/${bookingId}`, {
      method: 'DELETE',
    });
  }

  // Admin endpoints
  async getGUISettings() {
    return this.request('/api/admin/settings');
  }

  async updateGUISettings(settings: any) {
    return this.request('/api/admin/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  async getWorkDays(adminId: string) {
    return this.request('/api/admin/work-days', {
      headers: {
        'x-admin-id': adminId,
      },
    });
  }

  async addWorkDay(date: string, timeSlots: string[], adminId: string) {
    const body = { date, time_slots: timeSlots };
    return this.request('/api/admin/add-work-day', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: {
        'x-admin-id': adminId,
      },
    });
  }

  async addTimeSlot(adminId: string, date: string, time: string) {
    console.log(`[API] addTimeSlot → date: ${date}, time: ${time}, adminId: ${adminId}`);
    return this.request('/api/admin/add-time-slot', {
      method: 'POST',
      body: JSON.stringify({ date, time }),
      headers: {
        'x-admin-id': adminId,
      },
    });
  }

  async deleteTimeSlot(adminId: string, date: string, time: string) {
    return this.request('/api/admin/delete-time-slot', {
      method: 'POST',
      body: JSON.stringify({ date, time }),
      headers: {
        'x-admin-id': adminId,
      },
    });
  }

  async deleteWorkDay(day_date: string) {
    return this.request('/api/admin/delete-work-day', {
      method: 'POST',
      body: JSON.stringify({ day_date }),
    });
  }

  async getBookingsForDate(date: string) {
    return this.request(`/api/admin/bookings/${date}`);
  }

  async openDay(date: string, adminId: string) {
    return this.request('/api/admin/open-day', {
      method: 'POST',
      headers: {
        'x-admin-id': adminId,
      },
      body: JSON.stringify({ date }),
    });
  }

  async closeDay(date: string, adminId: string) {
    return this.request('/api/admin/close-day', {
      method: 'POST',
      headers: {
        'x-admin-id': adminId,
      },
      body: JSON.stringify({ date }),
    });
  }

  // Новые методы для отмены и истории
  async cancelBookingWithReason(bookingId: number, reason: string) {
    return this.request(`/api/bookings/${bookingId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async getBookingHistory() {
    return this.request('/api/bookings/history');
  }

  async getCancelledBookings() {
    return this.request('/api/bookings/cancelled');
  }
}

export const apiClient = new ApiClient();
