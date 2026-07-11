import {
  Anchor,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import {
  Icon,
  IconAlertTriangle,
  IconBox,
  IconPlayerPause,
  IconPlayerPlay,
} from '@tabler/icons-react';
import { dirname } from 'pathe';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  GeneratorStats,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { StatusPill } from '@/components/ui/StatusPill';
import { ROUTE_PATHS } from '@/routing/paths';

function formatUptime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const d = Math.floor(s / 86_400);
  const h = Math.floor((s % 86_400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

interface StatusRailProps {
  generators: GeneratorsInfo;
  generatorsStats: GeneratorStats[];
}

export const StatusRail: FC<StatusRailProps> = ({
  generators,
  generatorsStats,
}) => {
  const navigate = useNavigate();

  const total = generators.length;
  const active = generators.filter((g) => g.status.is_running).length;
  const failed = generators.filter(
    (g) => g.status.is_ended_up && !g.status.is_ended_up_successfully
  ).length;
  const inactive = generators.filter(
    (g) =>
      !g.status.is_running &&
      (!g.status.is_ended_up || g.status.is_ended_up_successfully)
  ).length;

  const stats: {
    label: string;
    value: number;
    color: string;
    icon: Icon;
  }[] = [
    { label: 'Total', value: total, color: 'var(--ev-text)', icon: IconBox },
    {
      label: 'Active',
      value: active,
      color: active > 0 ? 'var(--ev-good)' : 'var(--ev-muted)',
      icon: IconPlayerPlay,
    },
    {
      label: 'Inactive',
      value: inactive,
      color: 'var(--ev-muted)',
      icon: IconPlayerPause,
    },
    {
      label: 'Failed',
      value: failed,
      color: failed > 0 ? 'var(--ev-bad)' : 'var(--ev-muted)',
      icon: IconAlertTriangle,
    },
  ];

  const uptimeById = new Map(generatorsStats.map((s) => [s.id, s.uptime]));

  const recent = [...generators]
    .sort(
      (a, b) =>
        Date.parse(b.start_time ?? '1970') - Date.parse(a.start_time ?? '1970')
    )
    .slice(0, 5);

  return (
    <Stack gap="lg">
      <Stack gap="xs">
        <Group justify="space-between" align="center">
          <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
            Instances
          </Text>
          <Anchor
            size="xs"
            style={{ cursor: 'pointer' }}
            onClick={() => void navigate(ROUTE_PATHS.MONITORING)}
          >
            Monitoring
          </Anchor>
        </Group>
        <Paper withBorder radius="md" p="lg">
          <Stack gap="md">
            <SimpleGrid cols={2} spacing="lg">
              {stats.map((s) => (
                <Stack key={s.label} gap={4}>
                  <Text fz="1.75rem" fw={700} lh={1} style={{ color: s.color }}>
                    {s.value}
                  </Text>
                  <Group gap={6} wrap="nowrap">
                    <s.icon
                      size={15}
                      stroke={1.5}
                      style={{ color: s.color, flexShrink: 0 }}
                    />
                    <Text size="xs" c="dimmed">
                      {s.label}
                    </Text>
                  </Group>
                </Stack>
              ))}
            </SimpleGrid>
            <Text size="xs" c="dimmed">
              {total > 0 ? `${active} of ${total} running` : 'No instances'}
            </Text>
          </Stack>
        </Paper>
      </Stack>

      <Stack gap="xs">
        <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
          Recent instances
        </Text>
        <Paper withBorder radius="md" p="xs">
          {recent.length === 0 ? (
            <Text size="sm" c="dimmed" ta="center" py="md">
              No instances yet.
            </Text>
          ) : (
            <Stack gap={2}>
              {recent.map((g) => {
                const uptime = uptimeById.get(g.id);
                const project = dirname(g.path);
                const subline =
                  g.status.is_running && uptime !== undefined
                    ? `${project} · up ${formatUptime(uptime)}`
                    : project;

                return (
                  <UnstyledButton
                    key={g.id}
                    p="xs"
                    style={{ borderRadius: 'var(--mantine-radius-sm)' }}
                    styles={{
                      root: {
                        '&:hover': {
                          backgroundColor: 'var(--mantine-color-default-hover)',
                        },
                      },
                    }}
                    onClick={() =>
                      void navigate(`${ROUTE_PATHS.INSTANCES}/${g.id}`)
                    }
                  >
                    <Group gap="sm" justify="space-between" wrap="nowrap">
                      <Stack gap={0} style={{ minWidth: 0 }}>
                        <Text size="sm" fw={500} truncate>
                          {g.id}
                        </Text>
                        <Text size="xs" c="dimmed" truncate>
                          {subline}
                        </Text>
                      </Stack>
                      <StatusPill status={g.status} />
                    </Group>
                  </UnstyledButton>
                );
              })}
            </Stack>
          )}
        </Paper>
      </Stack>
    </Stack>
  );
};
