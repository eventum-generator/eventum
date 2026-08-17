import {
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import bytes from 'bytes';
import { FC, ReactNode } from 'react';

import { formatSeconds, formatUptime } from '../format';
import { Section, SectionLabel } from '../primitives';
import { ResourcesStats } from '@/api/routes/generators/schemas';
import { CPU_THRESHOLDS, levelColor } from '@/utils/levelColor';

/**
 * A queue fill level as a labelled bar. A queue is held back by whichever
 * of its two limits it reaches first, so the bar follows the fuller of the
 * batches it holds and the memory they occupy.
 */
const QueueFill: FC<{
  label: string;
  size: number;
  maxsize: number;
  sizeBytes: number;
  maxBytes: number | null;
}> = ({ label, size, maxsize, sizeBytes, maxBytes }) => {
  const batchPercent = (size / maxsize) * 100;
  const bytePercent = maxBytes ? (sizeBytes / maxBytes) * 100 : 0;
  const percent = Math.max(batchPercent, bytePercent);

  return (
    <Stack gap={4}>
      <Group justify="space-between" gap="xs">
        <Text size="xs" c="dimmed">
          {label}
        </Text>
        <Text size="xs" ff="monospace">
          {size} / {maxsize}
        </Text>
      </Group>
      <Progress
        value={percent}
        color={percent >= 100 ? 'yellow' : 'primary'}
        size="sm"
        aria-label={`${label} queue fill`}
      />
      <Text size="xs" c="dimmed" ff="monospace">
        {formatBytes(sizeBytes)}
        {maxBytes !== null && ` / ${formatBytes(maxBytes)}`}
      </Text>
    </Stack>
  );
};

/** One figure with its caption underneath. */
const Figure: FC<{ label: string; value: string; color?: string }> = ({
  label,
  value,
  color,
}) => (
  <Stack gap={2}>
    <Text size="xl" fw={600} c={color}>
      {value}
    </Text>
    <Text size="xs" c="dimmed">
      {label}
    </Text>
  </Stack>
);

const formatBytes = (value: number) =>
  bytes(value, { decimalPlaces: 1 }) ?? '0';

/** One group of related figures under its own heading. */
const Aspect: FC<{ label: string; children: ReactNode }> = ({
  label,
  children,
}) => (
  <Stack gap="sm">
    <SectionLabel>{label}</SectionLabel>
    {children}
  </Stack>
);

interface ResourcesPanelProps {
  resources: ResourcesStats;
  cpuPercent: number;
}

/**
 * What the instance costs the host it shares with the others, grouped by what
 * each figure answers: the processor it takes and whether it waits for one,
 * the memory its queues hold, and the bytes it moves. A queue that stays full
 * is the instance waiting on its own next stage, so it reads as the pressure
 * inside the pipeline rather than a fault, while a growing wait means the host
 * has more instances than processors.
 *
 * Memory beyond the queues is deliberately absent - instances share one
 * process heap, so no per-instance figure for it exists to report.
 */
export const ResourcesPanel: FC<ResourcesPanelProps> = ({
  resources,
  cpuPercent,
}) => (
  <Section label="Resources">
    <SimpleGrid cols={{ base: 1, md: 3 }} spacing="xl" verticalSpacing="lg">
      <Aspect label="Processor">
        <SimpleGrid cols={2} spacing="md">
          <Tooltip label="Share of one CPU core over the last poll interval">
            <Figure
              label="CPU"
              value={`${cpuPercent.toFixed(1)}%`}
              color={
                cpuPercent >= CPU_THRESHOLDS.warn
                  ? levelColor(
                      cpuPercent,
                      CPU_THRESHOLDS.warn,
                      CPU_THRESHOLDS.bad
                    )
                  : undefined
              }
            />
          </Tooltip>
          <Figure
            label="CPU time"
            value={formatUptime(resources.cpu_seconds)}
          />
          <Tooltip label="Time the threads were ready to run but waited for a processor">
            <Figure
              label="Wait"
              value={formatSeconds(resources.run_delay_seconds)}
            />
          </Tooltip>
          <Figure label="Threads" value={String(resources.thread_count)} />
        </SimpleGrid>
      </Aspect>

      <Aspect label="Memory in queues">
        <Stack gap="md">
          <QueueFill
            label="Timestamps"
            size={resources.queues.timestamps.size}
            maxsize={resources.queues.timestamps.maxsize}
            sizeBytes={resources.queues.timestamps.size_bytes}
            maxBytes={resources.queues.timestamps.max_bytes}
          />
          <QueueFill
            label="Events"
            size={resources.queues.events.size}
            maxsize={resources.queues.events.maxsize}
            sizeBytes={resources.queues.events.size_bytes}
            maxBytes={resources.queues.events.max_bytes}
          />
        </Stack>
      </Aspect>

      <Aspect label="Input and output">
        <SimpleGrid cols={2} spacing="md">
          <Figure
            label="Disk written"
            value={formatBytes(resources.disk_written_bytes)}
          />
          <Figure
            label="Disk read"
            value={formatBytes(resources.disk_read_bytes)}
          />
          <Figure
            label="Sent"
            value={formatBytes(resources.network_sent_bytes)}
          />
          <Figure
            label="Received"
            value={formatBytes(resources.network_received_bytes)}
          />
        </SimpleGrid>
      </Aspect>
    </SimpleGrid>
  </Section>
);
