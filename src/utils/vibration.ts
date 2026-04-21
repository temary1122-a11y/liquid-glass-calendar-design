// ============================================================
// src/utils/vibration.ts — Совместимые вибрации (iOS/Android)
// ============================================================

const tg = () => window.Telegram?.WebApp;

/** Лёгкая вибрация — выбор элемента */
export function vibrateLight(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.impactOccurred('light');
  } else if (navigator.vibrate) {
    navigator.vibrate(10);
  }
}

/** Средняя вибрация — нажатие кнопки */
export function vibrateMedium(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.impactOccurred('medium');
  } else if (navigator.vibrate) {
    navigator.vibrate(25);
  }
}

/** Тяжёлая вибрация — важное действие */
export function vibrateHeavy(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.impactOccurred('heavy');
  } else if (navigator.vibrate) {
    navigator.vibrate(50);
  }
}

/** Вибрация успеха */
export function vibrateSuccess(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.notificationOccurred('success');
  } else if (navigator.vibrate) {
    navigator.vibrate([10, 30, 10]);
  }
}

/** Вибрация ошибки */
export function vibrateError(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.notificationOccurred('error');
  } else if (navigator.vibrate) {
    navigator.vibrate([50, 20, 50]);
  }
}

/** Вибрация предупреждения */
export function vibrateWarning(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.notificationOccurred('warning');
  } else if (navigator.vibrate) {
    navigator.vibrate([30, 10, 30]);
  }
}

/** Вибрация смены выбора */
export function vibrateSelection(): void {
  const haptic = tg()?.HapticFeedback;
  if (haptic) {
    haptic.selectionChanged();
  } else if (navigator.vibrate) {
    navigator.vibrate(8);
  }
}
