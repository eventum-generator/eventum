import { Box, Group, Text } from '@mantine/core';
import { CSSProperties, FC } from 'react';

import './InstanceStatusSummary.css';
import {
  AGGREGATE_DOT_COLOR,
  VARIANT_STYLE,
  summarizeInstanceStatuses,
} from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';

interface ChipProps {
  count: number;
  label: string;
  color: string;
  /** Halo color, set only on a bucket that counts live instances. */
  glow?: string;
  small?: boolean;
}

function Chip({
  count,
  label,
  color,
  glow,
  small = false,
}: Readonly<ChipProps>) {
  return (
    <Group gap={7} wrap="nowrap">
      <Box
        className="ev-status-dot"
        data-glow={!!glow}
        style={
          {
            '--ev-dot-size': small ? '7px' : '9px',
            '--ev-dot': color,
            '--ev-dot-glow': glow,
          } as CSSProperties
        }
      />
      <Text size={small ? 'xs' : 'sm'} c="dimmed">
        <Text
          span
          fw={small ? 600 : 700}
          style={{
            color: small
              ? 'var(--mantine-color-dimmed)'
              : 'var(--mantine-color-text)',
          }}
        >
          {count}
        </Text>{' '}
        {label}
      </Text>
    </Group>
  );
}

// Semantic dot color when the bucket is non-empty, faint at zero.
const dot = (count: number, color: string) =>
  count > 0 ? color : VARIANT_STYLE.idle.dot;

interface InstanceStatusSummaryProps {
  statuses: GeneratorStatus[];
}

/**
 * Fleet status as a compact hierarchy tree that branches to the right: active
 * and the inactive total on the left, with the inactive total branching into
 * finished / failed / idle. Shared by the Home rail and the Monitoring header.
 */
export const InstanceStatusSummary: FC<InstanceStatusSummaryProps> = ({
  statuses,
}) => {
  const s = summarizeInstanceStatuses(statuses);

  return (
    <div className="iss">
      <Chip
        count={s.active}
        label="active"
        color={dot(s.active, VARIANT_STYLE.good.dot)}
        glow={s.active > 0 ? VARIANT_STYLE.good.glow : undefined}
      />
      <div className="iss-branch">
        <Chip
          count={s.inactive}
          label="inactive"
          color={dot(s.inactive, AGGREGATE_DOT_COLOR)}
        />
        <span className="iss-trunk" />
        <div className="iss-children">
          <div className="iss-child">
            <Chip
              small
              count={s.finished}
              label="finished"
              color={dot(s.finished, VARIANT_STYLE.done.dot)}
            />
          </div>
          <div className="iss-child">
            <Chip
              small
              count={s.failed}
              label="failed"
              color={dot(s.failed, VARIANT_STYLE.bad.dot)}
            />
          </div>
          <div className="iss-child">
            <Chip
              small
              count={s.idle}
              label="idle"
              color={dot(s.idle, VARIANT_STYLE.idle.dot)}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
