import { FC, ReactNode } from 'react';

import { VARIANT_STYLE, Variant } from './statusPalette';

interface StatusChipProps {
  /** Semantic variant driving the soft background, text and dot color. */
  variant: Variant;
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
export const StatusChip: FC<StatusChipProps> = ({ variant, dot, children }) => {
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
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: s.dot,
            flexShrink: 0,
          }}
        />
      ) : (
        dot
      )}
      {children}
    </span>
  );
};
