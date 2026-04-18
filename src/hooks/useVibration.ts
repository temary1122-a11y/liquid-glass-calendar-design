// ─── useVibration Hook ─────────────────────────────────────────────────────────────
// Кастомный hook для вибраций на мобильных устройствах
// Использует Navigator.vibrate() API

import { useCallback } from 'react';

interface UseVibrationReturn {
  vibrate: (pattern: number | number[]) => boolean;
  stop: () => void;
  isSupported: boolean;
}

export const useVibration = (): UseVibrationReturn => {
  const isSupported = typeof navigator !== 'undefined' && 'vibrate' in navigator;

  const vibrate = useCallback((pattern: number | number[]): boolean => {
    if (!isSupported) return false;
    try {
      return navigator.vibrate(pattern);
    } catch (error) {
      console.error('Vibration error:', error);
      return false;
    }
  }, [isSupported]);

  const stop = useCallback((): void => {
    if (!isSupported) return;
    try {
      navigator.vibrate(0);
    } catch (error) {
      console.error('Vibration stop error:', error);
    }
  }, [isSupported]);

  return { vibrate, stop, isSupported };
};

export const VIBRATION_PATTERNS = {
  TAP: 10,
  SUCCESS: [50, 30, 50] as number[],
  ERROR: [100, 50, 100, 50, 100] as number[],
  DELETE: [30, 20, 30] as number[],
  IMPORTANT: [100, 50, 100, 50, 200] as number[],
  LIGHT: 5,
  MEDIUM: 15,
};
