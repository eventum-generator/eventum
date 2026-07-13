import { ActionIcon, Divider, Group, Stack, Text } from '@mantine/core';
import { IconExternalLink, IconFolder } from '@tabler/icons-react';
import { formatDistanceToNow } from 'date-fns';
import { dirname } from 'pathe';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import { Field } from '../primitives';
import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorParameters } from '@/api/routes/generators/schemas';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { ResponsibleCopyButton } from '@/components/ui/ResponsibleCopyButton';
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
  const projectPath = `${ROUTE_PATHS.PROJECTS}/${projectName}`;

  const { data: generators } = useGenerators();
  const startTime = generators?.find((g) => g.id === instanceId)?.start_time;

  return (
    <Stack gap="sm">
      <Field label="Project">
        <RecordNameLink to={projectPath}>
          <Group gap={6} wrap="nowrap" align="center" justify="flex-end">
            <IconFolder size={15} style={{ flexShrink: 0 }} />
            <Text fz="sm" fw={500} truncate>
              {projectName}
            </Text>
          </Group>
        </RecordNameLink>
      </Field>
      <Divider />
      <Field label="Configuration file">
        <Group gap={6} wrap="nowrap" align="center" justify="flex-end">
          <Text size="sm" ff="monospace" truncate title={generatorParams.path}>
            {generatorParams.path}
          </Text>
          <ResponsibleCopyButton
            content={generatorParams.path}
            label="Copy path"
            size="sm"
          />
          <ActionIcon
            component={Link}
            to={projectPath}
            variant="default"
            size="sm"
            title="Open in editor"
          >
            <IconExternalLink size={15} />
          </ActionIcon>
        </Group>
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
      <Field label="Started">
        <Text size="sm" fw={500}>
          {startTime
            ? formatDistanceToNow(Date.parse(startTime), { addSuffix: true })
            : 'Never'}
        </Text>
      </Field>
    </Stack>
  );
};
