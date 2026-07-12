import { Box, Group, Text } from '@mantine/core';
import { FC } from 'react';

import { summarizeInstanceStatuses } from './statusPalette';
import { GeneratorStatus } from '@/api/routes/generators/schemas';

interface ChipProps {
  count: number;
  label: string;
  color: string;
  small?: boolean;
}

function Chip({ count, label, color, small = false }: Readonly<ChipProps>) {
  return (
    <Group gap={7} wrap="nowrap">
      <Box
        style={{
          width: small ? 7 : 8,
          height: small ? 7 : 8,
          borderRadius: '50%',
          background: color,
          flexShrink: 0,
        }}
      />
      <Text size={small ? 'xs' : 'sm'} c="dimmed">
        <Text
          span
          fw={small ? 600 : 700}
          style={{ color: small ? 'var(--ev-muted)' : 'var(--ev-text)' }}
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
  count > 0 ? color : 'var(--ev-faint)';

interface InstanceStatusSummaryProps {
  statuses: GeneratorStatus[];
}

/**
 * Fleet status summary: active vs inactive at the top level, with the
 * inactive total (finished + failed + idle) broken down in parentheses.
 * Shared by the Home instances rail and the Monitoring header so they stay
 * in sync.
 */
export const InstanceStatusSummary: FC<InstanceStatusSummaryProps> = ({
  statuses,
}) => {
  const s = summarizeInstanceStatuses(statuses);

  return (
    <Group gap="lg" wrap="wrap" align="center">
      <Chip
        count={s.active}
        label="active"
        color={dot(s.active, 'var(--ev-good)')}
      />

      <Group gap="xs" wrap="nowrap" align="center">
        <Chip
          count={s.inactive}
          label="inactive"
          color={dot(s.inactive, 'var(--ev-muted)')}
        />
        <Text span size="sm" c="dimmed">
          (
        </Text>
        <Chip
          small
          count={s.finished}
          label="finished"
          color={dot(s.finished, 'var(--ev-done-dot)')}
        />
        <Chip
          small
          count={s.failed}
          label="failed"
          color={dot(s.failed, 'var(--ev-bad)')}
        />
        <Chip
          small
          count={s.idle}
          label="idle"
          color={dot(s.idle, 'var(--ev-muted)')}
        />
        <Text span size="sm" c="dimmed">
          )
        </Text>
      </Group>
    </Group>
  );
};
