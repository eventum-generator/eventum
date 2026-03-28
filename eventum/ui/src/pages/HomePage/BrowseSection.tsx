import { Group, Stack, Text, UnstyledButton } from '@mantine/core';
import {
  IconFolder,
  IconPlayerPlay,
  IconTransform,
} from '@tabler/icons-react';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { ROUTE_PATHS } from '@/routing/paths';

interface BrowseSectionProps {
  generators: GeneratorsInfo | undefined;
  scenarioCount: number | undefined;
}

export const BrowseSection: FC<BrowseSectionProps> = ({
  generators,
  scenarioCount,
}) => {
  const navigate = useNavigate();

  const projectCount = generators?.length;
  const activeCount = generators?.filter(
    (g) => g.status.is_running
  ).length;

  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Browse
      </Text>
      <Stack gap={4}>
        <UnstyledButton
          p="xs"
          style={{
            borderRadius: 'var(--mantine-radius-sm)',
          }}
          styles={{
            root: {
              '&:hover': {
                backgroundColor: 'var(--mantine-color-default-hover)',
              },
            },
          }}
          onClick={() => void navigate(ROUTE_PATHS.PROJECTS)}
        >
          <Group gap="xs" justify="space-between">
            <Group gap="xs">
              <IconFolder
                size={18}
                color="var(--mantine-primary-color-filled)"
              />
              <Text size="sm">Projects</Text>
            </Group>
            {projectCount !== undefined && (
              <Text size="xs" c="dimmed">
                {projectCount}
              </Text>
            )}
          </Group>
        </UnstyledButton>

        <UnstyledButton
          p="xs"
          style={{
            borderRadius: 'var(--mantine-radius-sm)',
          }}
          styles={{
            root: {
              '&:hover': {
                backgroundColor: 'var(--mantine-color-default-hover)',
              },
            },
          }}
          onClick={() => void navigate(ROUTE_PATHS.INSTANCES)}
        >
          <Group gap="xs" justify="space-between">
            <Group gap="xs">
              <IconPlayerPlay
                size={18}
                color="var(--mantine-primary-color-filled)"
              />
              <Text size="sm">Instances</Text>
            </Group>
            {activeCount !== undefined && (
              <Text size="xs" c="dimmed">
                {activeCount} active
              </Text>
            )}
          </Group>
        </UnstyledButton>

        <UnstyledButton
          p="xs"
          style={{
            borderRadius: 'var(--mantine-radius-sm)',
          }}
          styles={{
            root: {
              '&:hover': {
                backgroundColor: 'var(--mantine-color-default-hover)',
              },
            },
          }}
          onClick={() => void navigate(ROUTE_PATHS.SCENARIOS)}
        >
          <Group gap="xs" justify="space-between">
            <Group gap="xs">
              <IconTransform
                size={18}
                color="var(--mantine-primary-color-filled)"
              />
              <Text size="sm">Scenarios</Text>
            </Group>
            {scenarioCount !== undefined && (
              <Text size="xs" c="dimmed">
                {scenarioCount}
              </Text>
            )}
          </Group>
        </UnstyledButton>
      </Stack>
    </Stack>
  );
};
