import { useEffect, useRef, useState } from 'react';

const easeOutCubic = (t: number) => 1 - (1 - t) ** 3;

/**
 * Eases the returned value toward `target` whenever it changes, producing a
 * rolling-counter effect instead of a hard jump. Interrupts smoothly: a new
 * target animates from wherever the previous animation currently sits. Uses
 * requestAnimationFrame and holds no external dependencies.
 */
export function useAnimatedNumber(target: number, duration = 600): number {
  const [display, setDisplay] = useState(target);
  const displayRef = useRef(target);

  useEffect(() => {
    const from = displayRef.current;
    if (from === target) return;

    let raf = 0;
    let startTs = 0;
    const tick = (ts: number) => {
      if (startTs === 0) startTs = ts;
      const progress = Math.min(1, (ts - startTs) / duration);
      const next = from + (target - from) * easeOutCubic(progress);
      displayRef.current = next;
      setDisplay(next);
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return display;
}
