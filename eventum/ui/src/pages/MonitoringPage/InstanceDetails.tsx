import {
  Button,
  Divider,
  Drawer,
  Group,
  Paper,
  Progress,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
import {
  Icon,
  IconArrowsSplit2,
  IconClockPlay,
  IconCube,
  IconExternalLink,
  IconNetwork,
  IconServer,
} from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { formatCompact, formatEps, formatRate } from './format';
import { InstanceUsageRow } from './history';
import { formatUptime } from './metrics';
import { GeneratorStats, QueueStats } from '@/api/routes/generators/schemas';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  CPU_THRESHOLDS,
  QUEUE_THRESHOLDS,
  levelColor,
} from '@/utils/levelColor';

const DANGER = 'var(--mantine-color-red-text)';

const formatBytes = (value: number) =>
  bytes(value, { decimalPlaces: 1 }) ?? '0B';

const Label: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
    {children}
  </Text>
);

/** One of the four figures that answer "what is this instance doing". */
const Headline: FC<{ value: string; label: string; color?: string }> = ({
  value,
  label,
  color,
}) => (
  <Stack gap={2}>
    <Text
      size="lg"
      fw={700}
      ff="monospace"
      c={color}
      style={{ fontVariantNumeric: 'tabular-nums', lineHeight: 1.2 }}
    >
      {value}
    </Text>
    <Text size="xs" c="dimmed">
      {label}
    </Text>
  </Stack>
);

/** One named figure with an icon: a pipeline stage or a resource. */
const Line: FC<{
  icon: Icon;
  name: string;
  stage: string;
  value: string;
}> = ({ icon: LineIcon, name, stage, value }) => (
  <Group justify="space-between" gap="md" wrap="nowrap">
    <Group gap={7} wrap="nowrap" style={{ minWidth: 0 }}>
      <LineIcon size={15} stroke={1.6} color="var(--mantine-color-dimmed)" />
      <Text size="sm" fw={500} truncate>
        {name}
      </Text>
      <Text size="xs" c="dimmed">
        {stage}
      </Text>
    </Group>
    <Text
      size="sm"
      ff="monospace"
      fw={600}
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      {value}
    </Text>
  </Group>
);

/** A subordinate figure under a stage - a loss, or a rate behind a total. */
const Note: FC<{ label: string; value: string; color?: string }> = ({
  label,
  value,
  color,
}) => (
  <Group justify="space-between" gap="md" wrap="nowrap" pl={22}>
    <Text size="xs" c="dimmed">
      {label}
    </Text>
    <Text
      size="xs"
      ff="monospace"
      c={color ?? 'dimmed'}
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
      <Group justify="space-between" gap="xs" wrap="nowrap">
        <Text size="sm">{label}</Text>
        <Text size="xs" c="dimmed" ff="monospace">
          {queue.size} / {queue.maxsize} · {formatBytes(queue.size_bytes)}
          {queue.max_bytes !== null && ` / ${formatBytes(queue.max_bytes)}`}
        </Text>
      </Group>
      <Progress
        value={percent}
        color={percent >= QUEUE_THRESHOLDS.bad ? 'yellow' : 'primary'}
        size="sm"
        aria-label={`${label} queue fill`}
      />
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
 * without the page carrying everything about every instance at once. It opens
 * on the four figures that say whether the instance is well, then what each of
 * its plugins moved, what it occupies, and how full its queues are. The
 * instance's own page is one link away for anything beyond that.
 */
export const InstanceDetails: FC<InstanceDetailsProps> = ({
  id,
  row,
  stats,
  onClose,
}) => {
  const failed =
    stats === undefined
      ? 0
      : stats.output.reduce(
          (sum, plugin) => sum + plugin.write_failed + plugin.format_failed,
          0
        );

  return (
    <Drawer
      opened={id !== null}
      onClose={onClose}
      position="right"
      size={400}
      padding="lg"
      title={
        <Stack gap={0}>
          <Text fw={650} style={{ wordBreak: 'break-all' }}>
            {id}
          </Text>
          {stats && (
            <Text size="xs" c="dimmed">
              running for {formatUptime(stats.uptime)}
            </Text>
          )}
        </Stack>
      }
    >
      {!stats || !row ? (
        <Text size="sm" c="dimmed">
          The instance is no longer running.
        </Text>
      ) : (
        <Stack gap="lg">
          <Paper withBorder p="md" bg="var(--mantine-color-default)">
            <SimpleGrid cols={2} spacing="md" verticalSpacing="md">
              <Headline
                value={`${formatEps(row.outputEps)}/s`}
                label="written now"
              />
              <Headline
                value={`${row.cpuPercent.toFixed(1)}%`}
                label="of a core"
                color={
                  row.cpuPercent >= CPU_THRESHOLDS.warn
                    ? levelColor(
                        row.cpuPercent,
                        CPU_THRESHOLDS.warn,
                        CPU_THRESHOLDS.bad
                      )
                    : undefined
                }
              />
              <Headline
                value={`${formatEps(row.failEps)}/s`}
                label="failing"
                color={row.failEps > 0 ? DANGER : undefined}
              />
              <Headline
                value={`${Math.round(row.queuePercent)}%`}
                label="events queue"
                color={
                  row.queuePercent >= QUEUE_THRESHOLDS.warn
                    ? levelColor(
                        row.queuePercent,
                        QUEUE_THRESHOLDS.warn,
                        QUEUE_THRESHOLDS.bad
                      )
                    : undefined
                }
              />
            </SimpleGrid>
          </Paper>

          <Stack gap={8}>
            <Label>Pipeline</Label>
            {stats.input.map((plugin) => (
              <Line
                key={`in-${plugin.plugin_id}`}
                icon={IconClockPlay}
                name={plugin.plugin_name}
                stage="input"
                value={`${formatCompact(plugin.generated)} generated`}
              />
            ))}
            <Line
              icon={IconCube}
              name={stats.event.plugin_name}
              stage="event"
              value={`${formatCompact(stats.event.produced)} produced`}
            />
            {stats.event.dropped > 0 && (
              <Note
                label="dropped"
                value={formatCompact(stats.event.dropped)}
              />
            )}
            {stats.event.produce_failed > 0 && (
              <Note
                label="failed to produce"
                value={formatCompact(stats.event.produce_failed)}
                color={DANGER}
              />
            )}
            {stats.output.map((plugin) => (
              <Line
                key={`out-${plugin.plugin_id}`}
                icon={IconArrowsSplit2}
                name={plugin.plugin_name}
                stage="output"
                value={`${formatCompact(plugin.written)} written`}
              />
            ))}
            {failed > 0 && (
              <Note
                label="failed to write or format"
                value={formatCompact(failed)}
                color={DANGER}
              />
            )}
          </Stack>

          <Divider />

          <Stack gap={8}>
            <Label>Resources</Label>
            <SimpleGrid cols={2} spacing="md" verticalSpacing="xs">
              <Headline
                value={formatUptime(stats.resources.cpu_seconds)}
                label="processor time"
              />
              <Headline
                value={`${row.waitPercent.toFixed(1)}%`}
                label="waiting for a core"
              />
              <Headline value={String(row.threads)} label="threads" />
              <Headline
                value={`${formatEps(stats.output_eps)}/s`}
                label="written on average"
              />
            </SimpleGrid>
            <Divider my={4} variant="dashed" />
            <Line
              icon={IconServer}
              name="Disk"
              stage="written"
              value={formatRate(row.diskWriteBps)}
            />
            <Note
              label="since it started"
              value={formatBytes(stats.resources.disk_written_bytes)}
            />
            <Line
              icon={IconNetwork}
              name="Network"
              stage="sent"
              value={formatRate(row.netSentBps)}
            />
            <Note
              label="since it started"
              value={formatBytes(stats.resources.network_sent_bytes)}
            />
          </Stack>

          <Divider />

          <Stack gap="sm">
            <Label>Queues</Label>
            <Queue
              label="Timestamps"
              queue={stats.resources.queues.timestamps}
            />
            <Queue label="Events" queue={stats.resources.queues.events} />
          </Stack>

          <Button
            component={Link}
            to={`${ROUTE_PATHS.INSTANCES}/${id}`}
            variant="default"
            leftSection={<IconExternalLink size={16} />}
            fullWidth
          >
            Open the instance page
          </Button>
        </Stack>
      )}
    </Drawer>
  );
};
