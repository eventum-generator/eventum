import {
  Anchor,
  Group,
  Paper,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { dirname } from 'pathe';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import {
  GeneratorStats,
  GeneratorsInfo,
} from '@/api/routes/generators/schemas';
import { InstanceStatusSummary } from '@/components/ui/InstanceStatusSummary';
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
  const total = generators.length;

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
          <Anchor size="xs" component={Link} to={ROUTE_PATHS.MONITORING}>
            Monitoring
          </Anchor>
        </Group>
        <Paper withBorder radius="md" p="lg">
          <Group justify="space-between" wrap="wrap" gap="md" align="center">
            <Group align="baseline" gap={8} wrap="nowrap">
              <Text
                fw={700}
                lh={1}
                style={{
                  fontSize: '2.25rem',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {total}
              </Text>
              <Text size="sm" c="dimmed">
                {total === 1 ? 'instance' : 'instances'}
              </Text>
            </Group>
            {total > 0 && (
              <InstanceStatusSummary
                statuses={generators.map((g) => g.status)}
              />
            )}
          </Group>
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
                    component={Link}
                    to={`${ROUTE_PATHS.INSTANCES}/${g.id}`}
                    p="xs"
                    style={{
                      borderRadius: 'var(--mantine-radius-sm)',
                      color: 'inherit',
                    }}
                    styles={{
                      root: {
                        '&:hover': {
                          backgroundColor: 'var(--mantine-color-default-hover)',
                        },
                      },
                    }}
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
