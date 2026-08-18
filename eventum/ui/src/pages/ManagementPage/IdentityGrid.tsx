import { Anchor, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import {
  IconArrowRight,
  IconBox,
  IconGauge,
  IconServer,
} from '@tabler/icons-react';
import bytes from 'bytes';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import { formatFreq } from './format';
import { Attr, AttrValue, InfoCard, LiveUptime, Meter } from './primitives';
import { InstanceInfo } from '@/api/routes/instance/schemas';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  CPU_THRESHOLDS,
  FD_THRESHOLDS,
  MEMORY_THRESHOLDS,
  levelColor,
} from '@/utils/levelColor';

const HEAD_ICON = { size: 18, stroke: 1.6 };

/** A CPU/memory snapshot: a labelled percentage over a thin bar, with a
 *  free-text caption below (cores/frequency, used/total). */
const Vital: FC<{
  label: string;
  pct: number;
  color: string;
  caption: string;
}> = ({ label, pct, color, caption }) => (
  <Stack gap={6}>
    <Group justify="space-between" align="baseline" wrap="nowrap">
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text
        size="sm"
        fw={600}
        ff="monospace"
        style={{ color, fontVariantNumeric: 'tabular-nums' }}
      >
        {Math.round(pct)}%
      </Text>
    </Group>
    <Meter pct={pct} color={color} />
    <Text size="xs" c="dimmed">
      {caption}
    </Text>
  </Stack>
);

export const IdentityGrid: FC<{ info: InstanceInfo }> = ({ info }) => {
  const memPct =
    info.memory_total_bytes > 0
      ? (info.memory_used_bytes / info.memory_total_bytes) * 100
      : 0;
  const fdPct =
    info.process_max_fds > 0
      ? (info.process_open_fds / info.process_max_fds) * 100
      : 0;

  return (
    <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
      <InfoCard icon={<IconBox {...HEAD_ICON} />} title="Application">
        <Attr label="Version">
          <AttrValue>{info.app_version}</AttrValue>
        </Attr>
        <Attr label="Python">
          <AttrValue>{info.python_version}</AttrValue>
        </Attr>
        <Attr label="Implementation">
          <AttrValue>{info.python_implementation}</AttrValue>
        </Attr>
        <Attr label="Compiler">
          <AttrValue title={info.python_compiler}>
            {info.python_compiler}
          </AttrValue>
        </Attr>
      </InfoCard>

      <InfoCard icon={<IconServer {...HEAD_ICON} />} title="Host">
        <Attr label="Hostname">
          <AttrValue title={info.host_name}>{info.host_name}</AttrValue>
        </Attr>
        <Attr label="IP address">
          <AttrValue>{info.host_ip_v4}</AttrValue>
        </Attr>
        <Attr label="Platform">
          <AttrValue title={info.platform}>{info.platform}</AttrValue>
        </Attr>
        <Attr label="Uptime">
          <AttrValue>
            <LiveUptime sinceEpochSeconds={info.boot_timestamp} />
          </AttrValue>
        </Attr>
      </InfoCard>

      <InfoCard icon={<IconGauge {...HEAD_ICON} />} title="System load">
        <Vital
          label="CPU"
          pct={info.cpu_percent}
          color={levelColor(
            info.cpu_percent,
            CPU_THRESHOLDS.warn,
            CPU_THRESHOLDS.bad
          )}
          caption={`${info.cpu_count ?? '?'} cores · ${formatFreq(
            info.cpu_frequency_mhz
          )}`}
        />
        <Vital
          label="Memory"
          pct={memPct}
          color={levelColor(
            memPct,
            MEMORY_THRESHOLDS.warn,
            MEMORY_THRESHOLDS.bad
          )}
          caption={`${bytes(info.memory_used_bytes)} / ${bytes(
            info.memory_total_bytes
          )} · app ${bytes(info.process_memory_bytes)}`}
        />
        <Vital
          label="Descriptors"
          pct={fdPct}
          color={levelColor(fdPct, FD_THRESHOLDS.warn, FD_THRESHOLDS.bad)}
          caption={`${info.process_open_fds} open of ${
            info.process_max_fds || '?'
          }`}
        />
        <Anchor
          component={Link}
          to={ROUTE_PATHS.MONITORING}
          size="xs"
          fw={500}
          mt="auto"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
        >
          Live metrics
          <IconArrowRight size={13} stroke={1.75} />
        </Anchor>
      </InfoCard>
    </SimpleGrid>
  );
};
