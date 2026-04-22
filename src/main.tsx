import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

// Initialize Telegram Web App
if (typeof window !== 'undefined' && (window as any).Telegram?.WebApp) {
  const tg = (window as any).Telegram.WebApp;
  tg.ready();
  tg.expand();

  // Detect device performance for animation optimization
  const platform = tg.platform || 'unknown';
  const isLowPerformance = platform === 'android' || platform === 'ios';
  (window as any).__LOW_PERFORMANCE__ = isLowPerformance;
} else {
  // Fallback for non-Telegram environments
  (window as any).__LOW_PERFORMANCE__ = false;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
