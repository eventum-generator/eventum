import {
  Anchor,
  Divider,
  Drawer,
  Group,
  Progress,
  Stack,
  Text,
} from '@mantine/core';
import { IconExternalLink } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { formatCompact, formatEps, formatRate } from './format';
import { InstanceUsageRow } from './history';
import { formatUptime } from './metrics';
import { GeneratorStats, QueueStats } from '@/api/routes/generators/schemas';
import { ROUTE_PATHS } from '@/routing/paths';
import { QUEUE_THRESHOLDS, levelColor } from '@/utils/levelColor';

const formatBytes = (value: number) =>
  bytes(value, { decimalPlaces: 1 }) ?? '0B';

const Label: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
    {children}
  </Text>
);

/** One labelled figure on its own line. */
const Line: FC<{ label: string; value: string; color?: string }> = ({
  label,
  value,
  color,
}) => (
  <Group justify="space-between" gap="md" wrap="nowrap">
    <Text size="sm" c="dimmed">
      {label}
    </Text>
    <Text
      size="sm"
      ff="monospace"
      fw={600}
      c={color}
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      {value}
    </Text>
  </Group>
);

/** A queue with the fuller of its two limits as the bar. */
const Queue: FC<{ label: string; queue: QueueStats }> = ({ label, queue }) => {
  const batches = queue.maxsize > 0 ? (queue.size / queue.maxsize) * 100 : 0;
  const held = queue.max_bytes ? (queue.size_bytes / queue.max_bytes) * 100 : 0;
  const percent = Math.max(batches, held);

  return (
    <Stack gap={4}>
      <Group justify="space-between" gap="xs">
        <Text size="sm" c="dimmed">
          {label}
        </Text>
        <Text size="sm" ff="monospace">
          {queue.size} / {queue.maxsize}
        </Text>
      </Group>
      <Progress
        value={percent}
        color={percent >= QUEUE_THRESHOLDS.bad ? 'yellow' : 'primary'}
        size="sm"
        aria-label={`${label} queue fill`}
      />
      <Text size="xs" c="dimmed" ff="monospace">
        {formatBytes(queue.size_bytes)}
        {queue.max_bytes !== null && ` / ${formatBytes(queue.max_bytes)}`}
      </Text>
    </Stack>
  );
};

interface InstanceDetailsProps {
  id: string | null;
  row: InstanceUsageRow | undefined;
  stats: GeneratorStats | undefined;
  onClose: () => void;
}

/**
 * Details of one instance beside the table, so a row can be looked into
 * without the page carrying everything about every instance at once. What is
 * here is what the table cannot fit: the totals behind the rates, the
 * per-plugin split, and the state of both queues. The instance's own page is
 * one link away for anything beyond that.
 */
export const InstanceDetails: FC<InstanceDetailsProps> = ({
  id,
  row,
  stats,
  onClose,
}) => (
  <Drawer
    opened={id !== null}
    onClose={onClose}
    position="right"
    size={380}
    title={
      <Text fw={650} style={{ wordBreak: 'break-all' }}>
        {id}
      </Text>
    }
  >
    {!stats || !row ? (
      <Text size="sm" c="dimmed">
        The instance is no longer running.
      </Text>
    ) : (
      <Stack gap="lg">
        <Anchor
          component={Link}
          to={`${ROUTE_PATHS.INSTANCES}/${id}`}
          size="sm"
        >
          <Group gap={6} wrap="nowrap">
            <IconExternalLink size={15} />
            Open the instance page
          </Group>
        </Anchor>

        <Stack gap={6}>
          <Label>Throughput</Label>
          <Line label="Output now" value={`${formatEps(row.outputEps)}/s`} />
          <Line
            label="Output since start"
            value={`${formatEps(stats.output_eps)}/s`}
          />
          <Line label="Uptime" value={formatUptime(stats.uptime)} />
          <Divider my={4} />
          <Line
            label="Generated"
            value={formatCompact(stats.total_generated)}
          />
          <Line label="Produced" value={formatCompact(stats.event.produced)} />
          <Line label="Written" value={formatCompact(stats.total_written)} />
          <Line label="Dropped" value={formatCompact(stats.event.dropped)} />
        </Stack>

        <Stack gap={6}>
          <Label>Plugins</Label>
          {stats.input.map((plugin) => (
            <Line
              key={`in-${plugin.plugin_id}`}
              label={`${plugin.plugin_name} (input)`}
              value={formatCompact(plugin.generated)}
            />
          ))}
          <Line
            label={`${stats.event.plugin_name} (event)`}
            value={`${formatCompact(stats.event.produced)} produced`}
          />
          {stats.event.produce_failed > 0 && (
            <Line
              label="produce failed"
              value={formatCompact(stats.event.produce_failed)}
              color="var(--mantine-color-red-text)"
            />
          )}
          {stats.output.map((plugin) => (
            <Line
              key={`out-${plugin.plugin_id}`}
              label={`${plugin.plugin_name} (output)`}
              value={`${formatCompact(plugin.written)} written`}
            />
          ))}
          {stats.output.some(
            (plugin) => plugin.write_failed + plugin.format_failed > 0
          ) && (
            <Line
              label="write or format failed"
              value={formatCompact(
                stats.output.reduce(
                  (sum, plugin) =>
                    sum + plugin.write_failed + plugin.format_failed,
                  0
                )
              )}
              color="var(--mantine-color-red-text)"
            />
          )}
        </Stack>

        <Stack gap={6}>
          <Label>Resources</Label>
          <Line label="CPU" value={`${row.cpuPercent.toFixed(1)}% of a core`} />
          <Line
            label="CPU time"
            value={formatUptime(stats.resources.cpu_seconds)}
          />
          <Line
            label="Wait"
            value={`${row.waitPercent.toFixed(1)}% of a core`}
          />
          <Line label="Threads" value={String(row.threads)} />
          <Line
            label="Disk"
            value={`${formatBytes(stats.resources.disk_read_bytes)} in / ${formatBytes(stats.resources.disk_written_bytes)} out`}
          />
          <Line
            label="Network"
            value={`${formatBytes(stats.resources.network_received_bytes)} in / ${formatBytes(stats.resources.network_sent_bytes)} out`}
          />
          <Line label="Disk write" value={formatRate(row.diskWriteBps)} />
          <Line label="Network out" value={formatRate(row.netSentBps)} />
        </Stack>

        <Stack gap="sm">
          <Group justify="space-between" gap="md">
            <Label>Queues</Label>
            <Text
              size="xs"
              ff="monospace"
              c={levelColor(
                row.queuePercent,
                QUEUE_THRESHOLDS.warn,
                QUEUE_THRESHOLDS.bad
              )}
            >
              {Math.round(row.queuePercent)}% full
            </Text>
          </Group>
          <Queue label="Timestamps" queue={stats.resources.queues.timestamps} />
          <Queue label="Events" queue={stats.resources.queues.events} />
        </Stack>
      </Stack>
    )}
  </Drawer>
);
