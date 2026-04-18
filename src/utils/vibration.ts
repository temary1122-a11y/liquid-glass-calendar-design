// ─── Vibration utilities for iOS Haptic Feedback ────────────────────────────────

/**
 * Проверяет поддержку вибраций
 */
export const isVibrationSupported = (): boolean => {
  return typeof navigator !== 'undefined' && 'vibrate' in navigator;
};

/**
 * Легкая вибрация (tap, click)
 * Паттерн: короткая мягкая вибрация 50ms
 */
export const vibrateLight = (): void => {
  if (isVibrationSupported()) {
    try {
      navigator.vibrate(50);
    } catch (error) {
      console.warn('Vibration error:', error);
    }
  }
};

/**
 * Средняя вибрация (button press, selection)
 * Паттерн: 100ms вибрация
 */
export const vibrateMedium = (): void => {
  if (isVibrationSupported()) {
    try {
      navigator.vibrate(100);
    } catch (error) {
      console.warn('Vibration error:', error);
    }
  }
};

/**
 * Сильная вибрация (success, confirmation)
 * Паттерн: 150ms вибрация
 */
export const vibrateStrong = (): void => {
  if (isVibrationSupported()) {
    try {
      navigator.vibrate(150);
    } catch (error) {
      console.warn('Vibration error:', error);
    }
  }
};

/**
 * Вибрация успеха (двойная)
 * Паттерн: 50ms + пауза 50ms + 50ms
 */
export const vibrateSuccess = (): void => {
  if (isVibrationSupported()) {
    try {
      navigator.vibrate([50, 50, 50]);
    } catch (error) {
      console.warn('Vibration error:', error);
    }
  }
};

/**
 * Вибрация ошибки (тройная)
 * Паттерн: 50ms + пауза 30ms + 50ms + пауза 30ms + 50ms
 */
export const vibrateError = (): void => {
  if (isVibrationSupported()) {
    try {
      navigator.vibrate([50, 30, 50, 30, 50]);
    } catch (error) {
      console.warn('Vibration error:', error);
    }
  }
};

/**
 * Вибрация навигации (swipe, transition)
 * Паттерн: 30ms мягкая вибрация
 */
export const vibrateNavigation = (): void => {
  if (isVibrationSupported()) {
    try {
      navigator.vibrate(30);
    } catch (error) {
      console.warn('Vibration error:', error);
    }
  }
};
