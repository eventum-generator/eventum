import {
  PointerEvent as ReactPointerEvent,
  useCallback,
  useState,
} from 'react';

interface ResizableOptions {
  min: number;
  max: number;
  axis: 'x' | 'y';
  /** Invert delta when the handle sits before the panel it sizes. */
  invert?: boolean;
}

interface HandleProps {
  onPointerDown: (e: ReactPointerEvent) => void;
  onPointerMove: (e: ReactPointerEvent) => void;
  onPointerUp: (e: ReactPointerEvent) => void;
  onPointerCancel: (e: ReactPointerEvent) => void;
}

interface Resizable {
  size: number;
  dragging: boolean;
  handleProps: HandleProps;
}

/**
 * Pointer-driven panel resizing with no external dependency. The parent
 * keeps the size in state and spreads `handleProps` onto a resize gutter.
 */
export function useResizable(
  initial: number,
  { min, max, axis, invert = false }: ResizableOptions
): Resizable {
  const [size, setSize] = useState(initial);
  const [dragging, setDragging] = useState(false);
  const [start, setStart] = useState(0);
  const [origin, setOrigin] = useState(0);

  const onPointerDown = useCallback(
    (e: ReactPointerEvent) => {
      e.preventDefault();
      e.currentTarget.setPointerCapture(e.pointerId);
      setDragging(true);
      setStart(axis === 'x' ? e.clientX : e.clientY);
      setOrigin(size);
    },
    [axis, size]
  );

  const onPointerMove = useCallback(
    (e: ReactPointerEvent) => {
      if (!e.currentTarget.hasPointerCapture(e.pointerId)) {
        return;
      }
      const current = axis === 'x' ? e.clientX : e.clientY;
      const delta = (current - start) * (invert ? -1 : 1);
      setSize(Math.min(max, Math.max(min, origin + delta)));
    },
    [axis, start, origin, invert, min, max]
  );

  const stop = useCallback((e: ReactPointerEvent) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    setDragging(false);
  }, []);

  return {
    size,
    dragging,
    handleProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: stop,
      onPointerCancel: stop,
    },
  };
}
