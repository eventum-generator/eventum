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
import { FC, ReactNode } from 'react';

import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorParameters } from '@/api/routes/generators/schemas';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { ROUTE_PATHS } from '@/routing/paths';
import { projectOfConfig } from '@/utils/projectPath';

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
  const project = projectOfConfig(generatorParams.path);
  const { data: generators } = useGenerators();
  const startTime = generators?.find((g) => g.id === instanceId)?.start_time;

  return (
    <Stack gap="md">
      <Attr icon={<IconFolder size={16} />} label="Project">
        {project.inWorkspace ? (
          <RecordNameLink to={`${ROUTE_PATHS.PROJECTS}/${project.name}`}>
            <Text size="sm" fw={500} truncate>
              {project.name}
            </Text>
          </RecordNameLink>
        ) : (
          // A configuration outside the workspace has no project page
          // to open, so the path it was registered with is shown as it
          // is - that is the only place it can be found.
          <Text size="sm" fw={500} truncate title={generatorParams.path}>
            {generatorParams.path}
          </Text>
        )}
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
        <Text size="sm" fw={500} c={autostart ? undefined : 'dimmed'}>
          {autostart ? 'On' : 'Off'}
        </Text>
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
