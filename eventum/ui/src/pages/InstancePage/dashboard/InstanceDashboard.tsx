import { Box, Divider, Group, Skeleton, Stack, Text } from '@mantine/core';
import { FC, ReactNode, useEffect } from 'react';

import { formatCompact, formatEps, formatUptime } from '../format';
import { useGeneratorStats } from '@/api/hooks/useGenerators';
import { GeneratorStats } from '@/api/routes/generators/schemas';

const POLL_MS = 3000;

/** Compact metric readout: label over a bold monospace value. */
const Stat: FC<{
  label: string;
  value: string;
  unit?: string;
  color?: string;
}> = ({ label, value, unit, color }) => (
  <Box>
    <Text size="xs" tt="uppercase" lts="0.5px" fw={600} c="dimmed">
      {label}
    </Text>
    <Group gap={4} align="baseline" wrap="nowrap">
      <Text
        fw={700}
        ff="monospace"
        style={{
          fontSize: '1.05rem',
          lineHeight: 1.2,
          fontVariantNumeric: 'tabular-nums',
          color,
        }}
      >
        {value}
      </Text>
      {unit ? (
        <Text size="xs" c="dimmed">
          {unit}
        </Text>
      ) : null}
    </Group>
  </Box>
);

/** One counter inside a plugin row: number + dimmed label, red when > 0. */
const Count: FC<{ value: number; label: string; danger?: boolean }> = ({
  value,
  label,
  danger,
}) => (
  <Text size="sm" style={{ fontVariantNumeric: 'tabular-nums' }}>
    <Text
      span
      fw={600}
      style={{ color: danger && value > 0 ? 'var(--ev-bad)' : undefined }}
    >
      {value.toLocaleString()}
    </Text>{' '}
    <Text span c="dimmed" size="xs">
      {label}
    </Text>
  </Text>
);

/** A stage caption over one or more plugin rows. */
const Stage: FC<{ name: string; children: ReactNode }> = ({
  name,
  children,
}) => (
  <Stack gap={6}>
    <Text size="xs" tt="uppercase" lts="1px" fw={600} c="dimmed">
      {name}
    </Text>
    {children}
  </Stack>
);

const PluginRow: FC<{ name: string; counts: ReactNode }> = ({
  name,
  counts,
}) => (
  <Group justify="space-between" wrap="nowrap" gap="md" pl="xs">
    <Text size="sm" ff="monospace" truncate>
      {name}
    </Text>
    <Group gap="lg" wrap="nowrap">
      {counts}
    </Group>
  </Group>
);

function countErrors(stats: GeneratorStats): number {
  return (
    stats.event.produce_failed +
    stats.output.reduce((n, o) => n + o.write_failed + o.format_failed, 0)
  );
}

/**
 * Compact, dense view of a running instance: a one-line metric summary over a
 * per-plugin pipeline breakdown (input generation, event production, output
 * writes with their failures). Polls stats while mounted.
 */
export const InstanceDashboard: FC<{ instanceId: string }> = ({
  instanceId,
}) => {
  const { data: stats, refetch } = useGeneratorStats(instanceId);

  useEffect(() => {
    const interval = setInterval(() => void refetch(), POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!stats) {
    return <Skeleton h={220} radius="md" />;
  }

  const errors = countErrors(stats);

  return (
    <Stack gap="md">
      <Group gap="xl" wrap="wrap">
        <Stat
          label="Input"
          value={formatEps(stats.input_eps)}
          unit="eps"
          color="var(--ev-cyan)"
        />
        <Stat
          label="Output"
          value={formatEps(stats.output_eps)}
          unit="eps"
          color="var(--ev-accent)"
        />
        <Stat label="Generated" value={formatCompact(stats.total_generated)} />
        <Stat label="Written" value={formatCompact(stats.total_written)} />
        <Stat
          label="Errors"
          value={formatCompact(errors)}
          color={errors > 0 ? 'var(--ev-bad)' : undefined}
        />
        <Stat label="Dropped" value={formatCompact(stats.event.dropped)} />
        <Stat label="Uptime" value={formatUptime(stats.uptime)} />
      </Group>

      <Divider />

      <Stack gap="md">
        <Stage name="Input">
          {stats.input.map((p) => (
            <PluginRow
              key={`${p.plugin_name}-${p.plugin_id}`}
              name={`${p.plugin_name} #${p.plugin_id}`}
              counts={<Count value={p.generated} label="generated" />}
            />
          ))}
        </Stage>
        <Stage name="Event">
          <PluginRow
            name={`${stats.event.plugin_name} #${stats.event.plugin_id}`}
            counts={
              <>
                <Count value={stats.event.produced} label="produced" />
                <Count value={stats.event.dropped} label="dropped" />
                <Count
                  value={stats.event.produce_failed}
                  label="failed"
                  danger
                />
              </>
            }
          />
        </Stage>
        <Stage name="Output">
          {stats.output.map((p) => (
            <PluginRow
              key={`${p.plugin_name}-${p.plugin_id}`}
              name={`${p.plugin_name} #${p.plugin_id}`}
              counts={
                <>
                  <Count value={p.written} label="written" />
                  <Count value={p.write_failed} label="write failed" danger />
                  <Count value={p.format_failed} label="format failed" danger />
                </>
              }
            />
          ))}
        </Stage>
      </Stack>
    </Stack>
  );
};
