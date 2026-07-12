import { Anchor, Divider, Group, Stack, Text } from '@mantine/core';
import { IconFolder } from '@tabler/icons-react';
import { dirname } from 'pathe';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import { Field } from '../primitives';
import { GeneratorParameters } from '@/api/routes/generators/schemas';
import { ResponsibleCopyButton } from '@/components/ui/ResponsibleCopyButton';
import { ROUTE_PATHS } from '@/routing/paths';

interface WiringCardProps {
  generatorParams: GeneratorParameters;
  liveMode: boolean;
  autostart: boolean;
}

const yesNo = (v: boolean) => (
  <Text size="sm" fw={500}>
    {v ? 'Yes' : 'No'}
  </Text>
);

export const WiringCard: FC<WiringCardProps> = ({
  generatorParams,
  liveMode,
  autostart,
}) => {
  const projectName = dirname(generatorParams.path);

  return (
    <Stack gap="sm">
      <Field label="Project">
        <Anchor
          component={Link}
          to={`${ROUTE_PATHS.PROJECTS}/${projectName}`}
          underline="hover"
          c="inherit"
        >
          <Group gap={6} wrap="nowrap" align="center" justify="flex-end">
            <IconFolder
              size={15}
              color="var(--ev-muted)"
              style={{ flexShrink: 0 }}
            />
            <Text size="sm" fw={500} truncate>
              {projectName}
            </Text>
          </Group>
        </Anchor>
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
        </Group>
      </Field>
      <Divider />
      <Field label="Mode">
        <Text size="sm" fw={500}>
          {liveMode ? 'Live' : 'Sample'}
        </Text>
      </Field>
      <Divider />
      <Field label="Skip past">
        {yesNo(generatorParams.skip_past ?? false)}
      </Field>
      <Divider />
      <Field label="Autostart">{yesNo(autostart)}</Field>
      <Divider />
      <Field label="Timezone">
        <Text size="sm" fw={500}>
          {generatorParams.timezone ?? 'UTC'}
        </Text>
      </Field>
    </Stack>
  );
};
