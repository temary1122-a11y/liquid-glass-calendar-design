// Mock data for calendar application

export interface Client {
  id: number;
  name: string;
  time: string;
  date: string;
  service: string;
  username?: string;
  userId?: string;
  note?: string;
  status: 'pending' | 'confirmed';
}

// Тестовые данные удалены - используются реальные данные из API
export const AVAILABLE_SLOTS: Record<string, string[]> = {};
export const MOCK_CLIENTS: Client[] = [];
