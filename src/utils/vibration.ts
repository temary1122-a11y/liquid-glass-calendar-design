// ─── Vibration utilities for Telegram WebApp Haptic Feedback ────────────────
// ВАЖНО: impactOccurred и selectionChanged НЕ РАБОТАЮТ на Android (баг Telegram)
// Используем только notificationOccurred для совместимости с Android и iOS
// GitHub issue: https://github.com/Telegram-Mini-Apps/issues/issues/28

/**
 * Получает Telegram WebApp Haptic Feedback API
 */
const getHapticFeedback = () => {
  const tg = (window as any).Telegram?.WebApp;
  return tg?.HapticFeedback;
};

/**
 * Проверяет поддержку Haptic Feedback
 */
export const isVibrationSupported = (): boolean => {
  const haptic = getHapticFeedback();
  return !!haptic;
};

/**
 * Легкая вибрация (tap, click)
 * Использует notificationOccurred('success') для совместимости с Android
 */
export const vibrateLight = (): void => {
  const haptic = getHapticFeedback();
  console.log('vibrateLight called, haptic:', !!haptic);
  if (haptic) {
    try {
      haptic.notificationOccurred('success');
      console.log('vibrateLight executed');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  } else {
    console.warn('Haptic feedback not available');
  }
};

/**
 * Средняя вибрация (button press, selection)
 * Использует notificationOccurred('success') для совместимости с Android
 */
export const vibrateMedium = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.notificationOccurred('success');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Сильная вибрация (success, confirmation)
 * Использует notificationOccurred('success') для совместимости с Android
 */
export const vibrateStrong = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.notificationOccurred('success');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Вибрация успеха
 * Использует Telegram.WebApp.HapticFeedback.notificationOccurred('success')
 */
export const vibrateSuccess = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.notificationOccurred('success');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Вибрация ошибки
 * Использует Telegram.WebApp.HapticFeedback.notificationOccurred('error')
 */
export const vibrateError = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.notificationOccurred('error');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Вибрация предупреждения
 * Использует Telegram.WebApp.HapticFeedback.notificationOccurred('warning')
 */
export const vibrateWarning = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.notificationOccurred('warning');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Вибрация навигации (swipe, transition)
 * Использует notificationOccurred('success') для совместимости с Android
 * selectionChanged НЕ РАБОТАЕТ на Android
 */
export const vibrateNavigation = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.notificationOccurred('success');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};
