import {
  Center,
  Divider,
  Group,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { IconSearch } from '@tabler/icons-react';
import { FC, useMemo, useState } from 'react';

import { InstanceDetails } from './InstanceDetails';
import { InstancesTable } from './InstancesTable';
import { LoadChart } from './LoadChart';
import { SectionLabel } from './SectionLabel';
import {
  FlowPoint,
  InstanceUsageRow,
  LoadPoint,
  instanceBands,
} from './history';
import { instanceColors } from './instanceColors';
import { GeneratorStats } from '@/api/routes/generators/schemas';
import { QUEUE_THRESHOLDS } from '@/utils/levelColor';

/** Bands beyond this are summed into one, so the chart stays readable. */
const TOP_BANDS = 6;

/** An instance writing less than this is treated as idle. */
const IDLE_EPS = 1;

type Filter = 'all' | 'failing' | 'limit' | 'idle';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'failing', label: 'Failing' },
  { value: 'limit', label: 'At the limit' },
  { value: 'idle', label: 'Idle' },
];

function matches(row: InstanceUsageRow, filter: Filter): boolean {
  switch (filter) {
    case 'failing': {
      return row.failEps > 0;
    }
    case 'limit': {
      return row.queuePercent >= QUEUE_THRESHOLDS.bad;
    }
    case 'idle': {
      return row.outputEps < IDLE_EPS;
    }
    default: {
      return true;
    }
  }
}

interface InstancesSectionProps {
  rows: InstanceUsageRow[];
  load: LoadPoint[];
  flow: FlowPoint[];
  stats: GeneratorStats[];
  points: number;
}

/**
 * Every running instance in one place: what each of them contributes to the
 * output load, and what each of them occupies while doing it. The chart and
 * the table are two views of the same set - a search or a quick filter
 * narrows both, and selecting an instance in either one highlights it in the
 * other and opens its details.
 */
export const InstancesSection: FC<InstancesSectionProps> = ({
  rows,
  load,
  flow,
  stats,
  points,
}) => {
  const [groupBy, setGroupBy] = useState<'instance' | 'stage'>('instance');
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const colorOf = useMemo(
    () => instanceColors(rows.map((row) => row.id)),
    [rows]
  );

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter(
      (row) =>
        matches(row, filter) &&
        (needle === '' || row.id.toLowerCase().includes(needle))
    );
  }, [rows, filter, query]);

  const { ids: bandIds, rows: bands } = useMemo(() => {
    const shown = new Set(visible.map((row) => row.id));
    const narrowed = load.map((point) => ({
      ...point,
      written: Object.fromEntries(
        Object.entries(point.written).filter(([id]) => shown.has(id))
      ),
    }));
    return instanceBands(narrowed, TOP_BANDS);
  }, [load, visible]);

  const selectedRow = rows.find((row) => row.id === selectedId);
  const selectedStats = stats.find((entry) => entry.id === selectedId);

  return (
    <Stack gap="xs">
      <Group justify="space-between" gap="md" wrap="wrap">
        <SectionLabel>Instances</SectionLabel>
        <Text size="xs" c="dimmed">
          {visible.length === rows.length
            ? `${rows.length} running`
            : `${visible.length} of ${rows.length} running`}
        </Text>
      </Group>

      <Paper withBorder p="md">
        <Stack gap="sm">
          <Group justify="space-between" gap="sm" wrap="wrap">
            <SegmentedControl
              size="xs"
              value={groupBy}
              onChange={(value) =>
                setGroupBy(value === 'stage' ? 'stage' : 'instance')
              }
              data={[
                { value: 'instance', label: 'By instance' },
                { value: 'stage', label: 'By stage' },
              ]}
            />
            <Group gap="sm" wrap="wrap">
              <SegmentedControl
                size="xs"
                value={filter}
                onChange={(value) => setFilter(value as Filter)}
                data={FILTERS}
              />
              <TextInput
                size="xs"
                w={200}
                placeholder="Search instances"
                leftSection={<IconSearch size={14} />}
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
            </Group>
          </Group>

          <LoadChart
            bands={bands}
            bandIds={bandIds}
            colorOf={colorOf}
            flow={flow}
            groupBy={groupBy}
            points={points}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />

          <Divider />

          {visible.length === 0 ? (
            <Center h={80}>
              <Text size="sm" c="dimmed">
                No instances match the filter
              </Text>
            </Center>
          ) : (
            <InstancesTable
              rows={visible}
              colorOf={colorOf}
              selectedId={selectedId}
              onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
            />
          )}
        </Stack>
      </Paper>

      <InstanceDetails
        id={selectedId}
        row={selectedRow}
        stats={selectedStats}
        onClose={() => setSelectedId(null)}
      />
    </Stack>
  );
};
