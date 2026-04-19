import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  animate,
  useDragControls,
  useMotionValue,
} from "framer-motion";
import { useVibration, VIBRATION_PATTERNS } from "../hooks/useVibration";

export interface TimePickerProps {
  value: string; // "HH:mm"
  onChange: (time: string) => void; // live preview
  onConfirm?: () => void; // commit action in parent (optional)
  onClose: () => void; // close sheet
  open: boolean;
}

const TIME_PRESETS = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"] as const;

const MINUTE_STEP = 15;

const ITEM_HEIGHT = 36; // px
const WHEEL_HEIGHT = 216; // px
const WHEEL_PADDING = (WHEEL_HEIGHT - ITEM_HEIGHT) / 2;

type ParsedTime = { hour: number; minute: number };

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}
function pad2(n: number) {
  return String(n).padStart(2, "0");
}
function formatTime(hour: number, minute: number) {
  return `${pad2(hour)}:${pad2(minute)}`;
}
function defaultTime(): ParsedTime {
  return { hour: 9, minute: 0 };
}

function snapMinuteToStep(minute: number, step: number) {
  if (step <= 1) return clamp(minute, 0, 59);
  const q = Math.round(minute / step);
  const snapped = q * step;
  // don't jump hour (60 -> 45 for step 15)
  return snapped >= 60 ? 60 - step : clamp(snapped, 0, 59);
}

/** Parser "H:m"/"HH:mm" -> valid time or null */
function parseTimeString(value: string): ParsedTime | null {
  const v = (value ?? "").trim();
  const m = /^(\d{1,2}):(\d{1,2})$/.exec(v);
  if (!m) return null;

  const hour = Number(m[1]);
  const minute = Number(m[2]);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null;
  if (hour < 0 || hour > 23) return null;
  if (minute < 0 || minute > 59) return null;

  return { hour, minute: snapMinuteToStep(minute, MINUTE_STEP) };
}

function normalizeTime(value: string): string | null {
  const parsed = parseTimeString(value);
  if (!parsed) return null;
  return formatTime(parsed.hour, parsed.minute);
}

/** Body scroll lock (more stable in WebView/Telegram than just overflow:hidden) */
function useBodyScrollLock(locked: boolean) {
  useEffect(() => {
    if (!locked) return;

    const body = document.body;
    const scrollY = window.scrollY || window.pageYOffset;

    const prev = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
      overscrollBehavior: body.style.overscrollBehavior as string,
    };

    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    body.style.overflow = "hidden";
    body.style.overscrollBehavior = "none";

    return () => {
      body.style.position = prev.position;
      body.style.top = prev.top;
      body.style.left = prev.left;
      body.style.right = prev.right;
      body.style.width = prev.width;
      body.style.overflow = prev.overflow;
      body.style.overscrollBehavior = prev.overscrollBehavior;

      const y = Math.abs(parseInt(prev.top || "0", 10)) || scrollY;
      window.scrollTo(0, y);
    };
  }, [locked]);
}

type WheelProps = {
  ariaLabel: string;
  items: string[];
  index: number;
  onIndexChange: (nextIndex: number, meta: { source: "scroll" | "program" }) => void;
  className?: string;
};

function Wheel({ ariaLabel, items, index, onIndexChange, className }: WheelProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const ignoreScrollRef = useRef(false);

  const lastIndexRef = useRef<number>(index);
  const scrollEndTimerRef = useRef<number | null>(null);

  const scrollToIndex = useCallback(
    (i: number, behavior: ScrollBehavior) => {
      const el = ref.current;
      if (!el) return;

      const next = clamp(i, 0, items.length - 1);
      ignoreScrollRef.current = true;
      el.scrollTo({ top: next * ITEM_HEIGHT, behavior });

      window.setTimeout(() => {
        ignoreScrollRef.current = false;
      }, behavior === "smooth" ? 250 : 0);
    },
    [items.length]
  );

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const expectedTop = clamp(index, 0, items.length - 1) * ITEM_HEIGHT;
    if (Math.abs(el.scrollTop - expectedTop) < 0.5) return;

    scrollToIndex(index, "auto");
    lastIndexRef.current = index;
  }, [index, items.length, scrollToIndex]);

  const handleScroll = useCallback(() => {
    const el = ref.current;
    if (!el) return;

    const raw = el.scrollTop / ITEM_HEIGHT;
    const nextIndex = clamp(Math.round(raw), 0, items.length - 1);

    const source: "scroll" | "program" = ignoreScrollRef.current ? "program" : "scroll";

    if (nextIndex !== lastIndexRef.current) {
      lastIndexRef.current = nextIndex;
      onIndexChange(nextIndex, { source });
    }

    if (scrollEndTimerRef.current) window.clearTimeout(scrollEndTimerRef.current);
    scrollEndTimerRef.current = window.setTimeout(() => {
      scrollToIndex(nextIndex, "smooth");
    }, 120);
  }, [items.length, onIndexChange, scrollToIndex]);

  useEffect(() => {
    return () => {
      if (scrollEndTimerRef.current) window.clearTimeout(scrollEndTimerRef.current);
    };
  }, []);

  return (
    <div className={className}>
      <div
        ref={ref}
        aria-label={ariaLabel}
        role="listbox"
        tabIndex={0}
        onScroll={handleScroll}
        className={[
          "relative w-[7.5rem] select-none",
          "overflow-y-scroll overscroll-contain",
          "snap-y snap-mandatory",
          "focus:outline-none",
          "touch-pan-y",
          "[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
        ].join(" ")}
        style={{
          height: WHEEL_HEIGHT,
          paddingTop: WHEEL_PADDING,
          paddingBottom: WHEEL_PADDING,
          WebkitOverflowScrolling: "touch",
          scrollSnapType: "y mandatory",
        }}
      >
        {items.map((label, i) => {
          const selected = i === index;
          return (
            <div
              key={`${ariaLabel}-${label}-${i}`}
              role="option"
              aria-selected={selected}
              className={[
                "flex items-center justify-center snap-center px-2",
                selected ? "text-[#3d2b1f]" : "text-[#9e8476]",
              ].join(" ")}
              style={{
                height: ITEM_HEIGHT,
                scrollSnapAlign: "center",
                scrollSnapStop: "always",
                fontVariantNumeric: "tabular-nums",
                fontSize: 18,
                fontWeight: selected ? 600 : 500,
                letterSpacing: 0.2,
              }}
            >
              {label}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function makeHourItems() {
  return Array.from({ length: 24 }, (_, h) => pad2(h));
}
function makeMinuteItems(step: number) {
  const count = Math.floor(60 / step);
  return Array.from({ length: count }, (_, i) => pad2(i * step));
}

export default function TimePicker({ value, onChange, onConfirm, onClose, open }: TimePickerProps) {
  const { vibrate } = useVibration();

  const hours = useMemo(() => makeHourItems(), []);
  const minutes = useMemo(() => makeMinuteItems(MINUTE_STEP), []);

  const [hourIndex, setHourIndex] = useState<number>(() => defaultTime().hour);
  const [minuteIndex, setMinuteIndex] = useState<number>(() => defaultTime().minute / MINUTE_STEP);

  // value when opened (needed for rollback on cancel/backdrop/drag)
  const initialValueRef = useRef<string>(formatTime(defaultTime().hour, defaultTime().minute));
  const initialIndicesRef = useRef<{ h: number; m: number }>({ h: defaultTime().hour, m: 0 });

  // to avoid loops on live preview
  const lastEmittedValueRef = useRef<string | null>(null);

  // haptic throttling
  const lastHapticAtRef = useRef<number>(0);
  const hapticLightThrottled = useCallback(() => {
    const now = performance.now();
    if (now - lastHapticAtRef.current < 70) return;
    lastHapticAtRef.current = now;
    vibrate(VIBRATION_PATTERNS.LIGHT);
  }, [vibrate]);

  useBodyScrollLock(open);

  // Drag-to-close (via handle to not conflict with wheel scroll)
  const dragControls = useDragControls();
  const y = useMotionValue(0);

  const currentTimeString = useMemo(() => {
    const h = clamp(hourIndex, 0, 23);
    const m = clamp(minuteIndex * MINUTE_STEP, 0, 59);
    return formatTime(h, m);
  }, [hourIndex, minuteIndex]);

  // Sync on open
  useEffect(() => {
    if (!open) return;

    const normalized = normalizeTime(value);
    const init = normalized ?? formatTime(defaultTime().hour, defaultTime().minute);

    // if invalid value came - gently normalize outward so system is consistent
    if (!normalized) {
      // important: don't close, just correct value for AdminSchedulePanel
      onChange(init);
      lastEmittedValueRef.current = init;
    }

    const parsed = parseTimeString(init) ?? defaultTime();
    const nextH = parsed.hour;
    const nextM = Math.floor(parsed.minute / MINUTE_STEP);

    initialValueRef.current = formatTime(nextH, nextM * MINUTE_STEP);
    initialIndicesRef.current = { h: nextH, m: nextM };

    setHourIndex(nextH);
    setMinuteIndex(nextM);

    // reset drag position
    y.set(0);
  }, [open, value, onChange, y]);

  // If parent changed value externally while open (rare case) - adjust,
  // but don't react to own live-preview changes.
  useEffect(() => {
    if (!open) return;
    const normalized = normalizeTime(value);
    if (!normalized) return;
    if (normalized === lastEmittedValueRef.current) return;

    const parsed = parseTimeString(normalized);
    if (!parsed) return;

    setHourIndex(parsed.hour);
    setMinuteIndex(Math.floor(parsed.minute / MINUTE_STEP));
  }, [open, value]);

  const emitChange = useCallback(
    (nextTime: string) => {
      if (nextTime === lastEmittedValueRef.current) return;
      lastEmittedValueRef.current = nextTime;
      onChange(nextTime);
    },
    [onChange]
  );

  const handlePresetClick = useCallback(
    (t: string) => {
      const parsed = parseTimeString(t);
      if (!parsed) return;

      vibrate(VIBRATION_PATTERNS.LIGHT);

      const nextH = parsed.hour;
      const nextM = Math.floor(parsed.minute / MINUTE_STEP);

      setHourIndex(nextH);
      setMinuteIndex(nextM);

      emitChange(formatTime(nextH, nextM * MINUTE_STEP));
    },
    [emitChange, vibrate]
  );

  const revertAndClose = useCallback(() => {
    vibrate(VIBRATION_PATTERNS.LIGHT);

    const init = initialValueRef.current;
    const { h, m } = initialIndicesRef.current;

    // rollback preview outward
    emitChange(init);

    // and locally (in case parent doesn't update value before close)
    setHourIndex(h);
    setMinuteIndex(m);

    onClose();
  }, [emitChange, onClose, vibrate]);

  const handleConfirm = useCallback(() => {
    vibrate(VIBRATION_PATTERNS.SUCCESS);
    onConfirm?.();
    onClose();
  }, [onClose, onConfirm, vibrate]);

  const onHourIndexChange = useCallback(
    (next: number, meta: { source: "scroll" | "program" }) => {
      setHourIndex(next);
      if (meta.source === "scroll") {
        hapticLightThrottled();
        emitChange(formatTime(next, minuteIndex * MINUTE_STEP));
      }
    },
    [emitChange, hapticLightThrottled, minuteIndex]
  );

  const onMinuteIndexChange = useCallback(
    (next: number, meta: { source: "scroll" | "program" }) => {
      setMinuteIndex(next);
      if (meta.source === "scroll") {
        hapticLightThrottled();
        emitChange(formatTime(hourIndex, next * MINUTE_STEP));
      }
    },
    [emitChange, hapticLightThrottled, hourIndex]
  );

  const handleDragEnd = useCallback(
    (_: unknown, info: { offset: { y: number }; velocity: { y: number } }) => {
      const shouldClose = info.offset.y > 120 || info.velocity.y > 900;
      if (shouldClose) {
        // drag-down closes without saving
        revertAndClose();
        return;
      }
      animate(y, 0, { type: "spring", stiffness: 320, damping: 30 });
    },
    [revertAndClose, y]
  );

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop (close without saving) */}
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={revertAndClose}
          />

          {/* Sheet */}
          <motion.div
            className="fixed inset-x-0 bottom-0 z-50 flex justify-center"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 320 }}
            onClick={(e) => e.stopPropagation()}
          >
            <motion.div
              className="w-full max-w-lg rounded-t-3xl border-t border-white/30 bg-white/95 backdrop-blur-xl"
              style={{ y }}
              drag="y"
              dragControls={dragControls}
              dragListener={false}
              dragConstraints={{ top: 0, bottom: 0 }}
              dragElastic={0.12}
              onDragEnd={handleDragEnd}
            >
              {/* Grab handle (only it starts drag to not conflict with wheel) */}
              <div className="px-6 pt-3">
                <div
                  className="mx-auto h-1.5 w-10 rounded-full bg-[#e8e0d0]"
                  onPointerDown={(e) => {
                    // start drag
                    dragControls.start(e);
                  }}
                  style={{ touchAction: "none" }}
                />
              </div>

              {/* Header */}
              <div className="flex items-center justify-between border-b border-black/5 px-6 py-4">
                <motion.button
                  type="button"
                  whileTap={{ scale: 0.97 }}
                  onClick={revertAndClose}
                  className="text-sm font-medium text-[#9e8476]"
                >
                  Cancel
                </motion.button>

                <div className="flex items-center gap-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-[#a07060]">
                    <path d="M12 7v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10Z" stroke="currentColor" strokeWidth="2" />
                  </svg>
                  <span className="text-sm font-semibold text-[#3d2b1f]">Select Time</span>
                </div>

                <motion.button
                  type="button"
                  whileTap={{ scale: 0.97 }}
                  onClick={handleConfirm}
                  className="text-sm font-semibold text-[#2e7d5e]"
                >
                  Done
                </motion.button>
              </div>

              {/* Presets (only round hours) */}
              <div className="border-b border-black/5 px-6 py-3">
                <div className="flex gap-2 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                  {TIME_PRESETS.map((t) => {
                    const selected = currentTimeString === t;
                    return (
                      <motion.button
                        key={t}
                        type="button"
                        whileTap={{ scale: 0.97 }}
                        onClick={() => handlePresetClick(t)}
                        className={[
                          "shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                          selected
                            ? "bg-[#2e7d5e] text-white shadow-md"
                            : "bg-[#f5f0e8] text-[#7c5340] hover:bg-[#e8e0d0]",
                        ].join(" ")}
                      >
                        {t}
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* Wheels */}
              <div className="relative px-6 py-6">
                {/* Center highlight */}
                <div
                  className="pointer-events-none absolute left-6 right-6 top-1/2 -translate-y-1/2 rounded-2xl bg-white/60 ring-1 ring-black/5 backdrop-blur"
                  style={{ height: ITEM_HEIGHT + 6 }}
                />

                {/* Depth fades */}
                <div className="pointer-events-none absolute left-0 right-0 top-0 h-10 bg-gradient-to-b from-white/95 to-white/0" />
                <div className="pointer-events-none absolute left-0 right-0 bottom-0 h-10 bg-gradient-to-t from-white/95 to-white/0" />

                <div className="relative flex items-center justify-center gap-3">
                  <Wheel
                    ariaLabel="Hours"
                    items={hours}
                    index={hourIndex}
                    onIndexChange={onHourIndexChange}
                    className="min-w-[7.5rem]"
                  />

                  <div
                    className="pb-[2px] text-lg font-semibold text-[#9e8476]"
                    style={{ fontVariantNumeric: "tabular-nums" }}
                  >
                    :
                  </div>

                  <Wheel
                    ariaLabel="Minutes"
                    items={minutes}
                    index={minuteIndex}
                    onIndexChange={onMinuteIndexChange}
                    className="min-w-[7.5rem]"
                  />
                </div>

                {/* Current value hint */}
                <div className="mt-4 text-center text-xs font-medium text-[#9e8476]">
                  {currentTimeString}
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
