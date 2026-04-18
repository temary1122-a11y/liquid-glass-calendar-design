// ─── Vibration utilities for Telegram WebApp Haptic Feedback ────────────────

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
 * Использует Telegram.WebApp.HapticFeedback.impactOccurred('light')
 */
export const vibrateLight = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.impactOccurred('light');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Средняя вибрация (button press, selection)
 * Использует Telegram.WebApp.HapticFeedback.impactOccurred('medium')
 */
export const vibrateMedium = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.impactOccurred('medium');
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};

/**
 * Сильная вибрация (success, confirmation)
 * Использует Telegram.WebApp.HapticFeedback.impactOccurred('heavy')
 */
export const vibrateStrong = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.impactOccurred('heavy');
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
 * Использует Telegram.WebApp.HapticFeedback.selectionChanged()
 */
export const vibrateNavigation = (): void => {
  const haptic = getHapticFeedback();
  if (haptic) {
    try {
      haptic.selectionChanged();
    } catch (error) {
      console.warn('Haptic feedback error:', error);
    }
  }
};
