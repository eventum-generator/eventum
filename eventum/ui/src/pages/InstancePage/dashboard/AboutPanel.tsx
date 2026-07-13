import { Divider, Group, Stack, Text } from '@mantine/core';
import { IconFolder } from '@tabler/icons-react';
import { formatDistanceToNow } from 'date-fns';
import { dirname } from 'pathe';
import { FC } from 'react';

import { Field } from '../primitives';
import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorParameters } from '@/api/routes/generators/schemas';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { ROUTE_PATHS } from '@/routing/paths';

interface AboutPanelProps {
  instanceId: string;
  generatorParams: GeneratorParameters;
  liveMode: boolean;
}

export const AboutPanel: FC<AboutPanelProps> = ({
  instanceId,
  generatorParams,
  liveMode,
}) => {
  const projectName = dirname(generatorParams.path);

  const { data: generators } = useGenerators();
  const startTime = generators?.find((g) => g.id === instanceId)?.start_time;

  return (
    <Stack gap="sm">
      <Field label="Project">
        <RecordNameLink to={`${ROUTE_PATHS.PROJECTS}/${projectName}`}>
          <Group gap={6} wrap="nowrap" align="center" justify="flex-end">
            <IconFolder size={15} style={{ flexShrink: 0 }} />
            <Text fz="sm" fw={500} truncate>
              {projectName}
            </Text>
          </Group>
        </RecordNameLink>
      </Field>
      <Divider />
      <Field label="Mode">
        <Text size="sm" fw={500}>
          {liveMode ? 'Live' : 'Sample'}
        </Text>
      </Field>
      <Divider />
      <Field label="Timezone">
        <Text size="sm" fw={500}>
          {generatorParams.timezone ?? 'UTC'}
        </Text>
      </Field>
      <Divider />
      <Field label="Last started">
        <Text size="sm" fw={500}>
          {startTime
            ? formatDistanceToNow(Date.parse(startTime), { addSuffix: true })
            : 'Never'}
        </Text>
      </Field>
    </Stack>
  );
};
