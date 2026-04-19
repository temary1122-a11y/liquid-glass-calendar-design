// ─── Vibration utilities with fallback for different platforms ─────────────
// Приоритет: Telegram.WebApp.HapticFeedback > navigator.vibrate
// Оптимизация для iOS, Android, Web
// ВАЖНО: impactOccurred и selectionChanged НЕ РАБОТАЮТ на Android (баг Telegram)
// GitHub issue: https://github.com/Telegram-Mini-Apps/issues/issues/28

/**
 * Получает Telegram WebApp Haptic Feedback API
 */
const getHapticFeedback = () => {
  const tg = (window as any).Telegram?.WebApp;
  return tg?.HapticFeedback;
};

/**
 * Проверяет поддержку Haptic Feedback или navigator.vibrate
 */
export const isVibrationSupported = (): boolean => {
  const haptic = getHapticFeedback();
  const navigatorVibrate = 'vibrate' in navigator;
  return !!haptic || navigatorVibrate;
};

/**
 * Универсальная вибрация с fallback
 * 1. Telegram.WebApp.HapticFeedback (Mini App)
 * 2. navigator.vibrate (обычный браузер)
 */
const vibrate = (pattern: string | number | number[], type: 'telegram' | 'fallback'): void => {
  const haptic = getHapticFeedback();

  // Приоритет: Telegram WebApp HapticFeedback
  if (haptic && type === 'telegram') {
    try {
      if (typeof pattern === 'string') {
        haptic.notificationOccurred(pattern as 'success' | 'error' | 'warning');
      } else {
        // Для числовых паттернов используем notificationOccurred
        haptic.notificationOccurred('success');
      }
      console.log('Telegram HapticFeedback executed');
      return;
    } catch (error) {
      console.warn('Haptic feedback error, trying fallback:', error);
    }
  }

  // Fallback: navigator.vibrate
  if ('vibrate' in navigator) {
    try {
      // Если pattern - строка, конвертируем в числовой паттерн для fallback
      const numericPattern = typeof pattern === 'string' ? 50 : pattern;
      navigator.vibrate(numericPattern);
      console.log('navigator.vibrate executed:', numericPattern);
    } catch (error) {
      console.warn('navigator.vibrate error:', error);
    }
  } else {
    console.warn('Vibration not supported on this device');
  }
};

/**
 * Легкая вибрация (tap, click)
 * Telegram: notificationOccurred('success')
 * Fallback: navigator.vibrate(10)
 */
export const vibrateLight = (): void => {
  console.log('vibrateLight called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('success', 'telegram');
  } else {
    vibrate(10, 'fallback');
  }
};

/**
 * Средняя вибрация (button press, selection)
 * Telegram: notificationOccurred('success')
 * Fallback: navigator.vibrate(30)
 */
export const vibrateMedium = (): void => {
  console.log('vibrateMedium called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('success', 'telegram');
  } else {
    vibrate(30, 'fallback');
  }
};

/**
 * Сильная вибрация (success, confirmation)
 * Telegram: notificationOccurred('success')
 * Fallback: navigator.vibrate(50)
 */
export const vibrateStrong = (): void => {
  console.log('vibrateStrong called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('success', 'telegram');
  } else {
    vibrate(50, 'fallback');
  }
};

/**
 * Вибрация успеха
 * Telegram: notificationOccurred('success')
 * Fallback: navigator.vibrate([50, 50, 50])
 */
export const vibrateSuccess = (): void => {
  console.log('vibrateSuccess called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('success', 'telegram');
  } else {
    vibrate([50, 50, 50], 'fallback');
  }
};

/**
 * Вибрация ошибки
 * Telegram: notificationOccurred('error')
 * Fallback: navigator.vibrate([50, 30, 50, 30, 50])
 */
export const vibrateError = (): void => {
  console.log('vibrateError called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('error', 'telegram');
  } else {
    vibrate([50, 30, 50, 30, 50], 'fallback');
  }
};

/**
 * Вибрация предупреждения
 * Telegram: notificationOccurred('warning')
 * Fallback: navigator.vibrate([50, 50])
 */
export const vibrateWarning = (): void => {
  console.log('vibrateWarning called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('warning', 'telegram');
  } else {
    vibrate([50, 50], 'fallback');
  }
};

/**
 * Вибрация навигации (swipe, transition)
 * Telegram: notificationOccurred('success') (selectionChanged не работает на Android)
 * Fallback: navigator.vibrate(15)
 */
export const vibrateNavigation = (): void => {
  console.log('vibrateNavigation called');
  const haptic = getHapticFeedback();
  if (haptic) {
    vibrate('success', 'telegram');
  } else {
    vibrate(15, 'fallback');
  }
};
