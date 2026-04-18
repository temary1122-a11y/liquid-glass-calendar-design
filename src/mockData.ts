// Mock data for calendar application

export const AVAILABLE_SLOTS: Record<string, string[]> = {
  '2026-04-17': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'],
  '2026-04-18': ['09:00', '10:00', '11:00', '14:00'],
  '2026-04-19': ['09:00', '10:00', '14:00', '15:00', '16:00'],
  '2026-04-20': ['09:00', '10:00', '11:00', '14:00', '15:00'],
  '2026-04-21': ['09:00', '10:00', '14:00'],
};

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

export const MOCK_CLIENTS: Client[] = [
  {
    id: 1,
    name: 'Анастасия М.',
    time: '09:00',
    date: '2026-04-17',
    service: 'Наращивание ресниц',
    username: 'anastasia_m',
    status: 'confirmed',
  },
  {
    id: 2,
    name: 'Анна С.',
    time: '16:00',
    date: '2026-04-17',
    service: 'Наращивание ресниц',
    username: 'anna_s',
    status: 'pending',
  },
  {
    id: 3,
    name: 'Мария К.',
    time: '10:00',
    date: '2026-04-18',
    service: 'Наращивание ресниц',
    userId: '123456789',
    status: 'confirmed',
  },
];
