import { CSSProperties, FC, ReactNode } from 'react';

import { VARIANT_STYLE, Variant } from './statusPalette';

interface StatusChipProps {
  /** Semantic variant driving the soft background, text and dot color. */
  variant: Variant;
  /** Animate the default dot while the state is mid-transition. */
  processing?: boolean;
  /** Dot node rendered before the label. Defaults to a static dot in the
   *  variant's color; pass a custom node (e.g. a pulsing StatusDot) to
   *  override. `null` hides the dot entirely. */
  dot?: ReactNode;
  children: ReactNode;
}

/**
 * Rounded status pill - the single source of the pill look shared by the
 * instance StatusPill and the scenario status chips. Keeps every status
 * label in the app on the same shape, height and palette.
 */
export const StatusChip: FC<StatusChipProps> = ({
  variant,
  processing = false,
  dot,
  children,
}) => {
  const s = VARIANT_STYLE[variant];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 7,
        height: 24,
        padding: '0 10px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: 'nowrap',
        background: s.bg,
        color: s.fg,
      }}
    >
      {dot === undefined ? (
        <span
          className="ev-status-dot"
          data-glow={!!s.glow}
          data-processing={processing}
          style={
            { '--ev-dot': s.dot, '--ev-dot-glow': s.glow } as CSSProperties
          }
        />
      ) : (
        dot
      )}
      {children}
    </span>
  );
};
