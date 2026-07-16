import {
  IconAlertSquareRounded,
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoSquareRounded,
  type TablerIcon,
} from '@tabler/icons-react';
import { FC } from 'react';

export type AlertIconVariant = 'error' | 'info' | 'success' | 'warn';

export interface AlertIconProps {
  /** Selects both the glyph and its semantic color. */
  variant: AlertIconVariant;
  /** Icon size in px. Omit to use the icon's own default - matches every
   *  existing alert call site, none of which set an explicit size. */
  size?: number | string;
}

const VARIANT_ICON: Record<AlertIconVariant, TablerIcon> = {
  error: IconAlertSquareRounded,
  info: IconInfoSquareRounded,
  success: IconCircleCheck,
  warn: IconAlertTriangle,
};

const VARIANT_COLOR: Record<AlertIconVariant, string> = {
  error: 'var(--ev-bad)',
  info: 'var(--ev-info)',
  success: 'var(--ev-good)',
  warn: 'var(--ev-warn)',
};

/**
 * Icon for an Alert's `icon` slot, colored by semantic variant instead of a
 * raw Mantine color name. One glyph per variant, shared by every alert in
 * the app instead of each call site picking its own icon and color.
 */
export const AlertIcon: FC<AlertIconProps> = ({ variant, size }) => {
  const Icon = VARIANT_ICON[variant];
  return <Icon size={size} color={VARIANT_COLOR[variant]} />;
};
