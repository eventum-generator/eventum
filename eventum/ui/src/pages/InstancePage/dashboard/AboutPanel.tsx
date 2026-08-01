import { Box, Group, Stack, Text } from '@mantine/core';
import {
  IconActivityHeartbeat,
  IconClockHour4,
  IconDatabase,
  IconFolder,
  IconRocket,
  IconWorld,
} from '@tabler/icons-react';
import { formatDistanceToNow } from 'date-fns';
import { dirname } from 'pathe';
import { FC, ReactNode } from 'react';

import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorParameters } from '@/api/routes/generators/schemas';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { ROUTE_PATHS } from '@/routing/paths';

/** A definition row: icon + label on the left, value on the right. */
const Attr: FC<{ icon: ReactNode; label: string; children: ReactNode }> = ({
  icon,
  label,
  children,
}) => (
  <Group justify="space-between" wrap="nowrap" gap="md" align="center">
    <Group gap="sm" wrap="nowrap" align="center" style={{ flexShrink: 0 }}>
      <Box c="dimmed" style={{ display: 'flex' }}>
        {icon}
      </Box>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
    </Group>
    <Box style={{ minWidth: 0, textAlign: 'right' }}>{children}</Box>
  </Group>
);

/** A small on/off state chip: a coloured dot and label in a bordered pill. */
const StateChip: FC<{ on: boolean }> = ({ on }) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      height: 20,
      padding: '0 8px',
      borderRadius: 999,
      border: '1px solid var(--mantine-color-default-border)',
      fontSize: 11,
      fontWeight: 600,
      color: on
        ? 'var(--mantine-color-green-text)'
        : 'var(--mantine-color-dimmed)',
    }}
  >
    <span
      style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: on
          ? 'var(--mantine-color-green-text)'
          : 'var(--mantine-color-dimmed)',
      }}
    />
    {on ? 'On' : 'Off'}
  </span>
);

interface AboutPanelProps {
  instanceId: string;
  generatorParams: GeneratorParameters;
  liveMode: boolean;
  autostart: boolean;
}

export const AboutPanel: FC<AboutPanelProps> = ({
  instanceId,
  generatorParams,
  liveMode,
  autostart,
}) => {
  const projectName = dirname(generatorParams.path);
  const { data: generators } = useGenerators();
  const startTime = generators?.find((g) => g.id === instanceId)?.start_time;

  return (
    <Stack gap="md">
      <Attr icon={<IconFolder size={16} />} label="Project">
        <RecordNameLink to={`${ROUTE_PATHS.PROJECTS}/${projectName}`}>
          <Text size="sm" fw={500} truncate>
            {projectName}
          </Text>
        </RecordNameLink>
      </Attr>
      <Attr
        icon={
          liveMode ? (
            <IconActivityHeartbeat size={16} />
          ) : (
            <IconDatabase size={16} />
          )
        }
        label="Mode"
      >
        <Text size="sm" fw={500}>
          {liveMode ? 'Live' : 'Sample'}
        </Text>
      </Attr>
      <Attr icon={<IconRocket size={16} />} label="Autostart">
        <StateChip on={autostart} />
      </Attr>
      <Attr icon={<IconWorld size={16} />} label="Timezone">
        <Text size="sm" fw={500}>
          {generatorParams.timezone ?? 'UTC'}
        </Text>
      </Attr>
      <Attr icon={<IconClockHour4 size={16} />} label="Last run">
        <Text size="sm" c="dimmed">
          {startTime
            ? formatDistanceToNow(Date.parse(startTime), { addSuffix: true })
            : 'Never'}
        </Text>
      </Attr>
    </Stack>
  );
};
