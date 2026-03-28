import { Anchor, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconFolder, IconPlus, IconSearch } from '@tabler/icons-react';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import { CreateProjectModal } from '@/pages/ProjectsPage/CreateProjectModal';
import { ROUTE_PATHS } from '@/routing/paths';

interface StartSectionProps {
  existingProjectNames: string[];
}

export const StartSection: FC<StartSectionProps> = ({
  existingProjectNames,
}) => {
  const navigate = useNavigate();

  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Start
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
          onClick={() =>
            modals.open({
              title: 'New project',
              children: (
                <CreateProjectModal
                  existingProjectNames={existingProjectNames}
                />
              ),
              size: 'lg',
            })
          }
        >
          <Group gap="xs">
            <IconPlus size={18} color="var(--mantine-primary-color-filled)" />
            <Text size="sm">New Project...</Text>
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
          onClick={() => void navigate(ROUTE_PATHS.PROJECTS)}
        >
          <Group gap="xs">
            <IconFolder size={18} color="var(--mantine-primary-color-filled)" />
            <Text size="sm">Open Existing Project...</Text>
          </Group>
        </UnstyledButton>

        <Anchor
          href="https://eventum.run/hub"
          target="_blank"
          rel="noopener noreferrer"
          underline="never"
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
        >
          <Group gap="xs">
            <IconSearch size={18} color="var(--mantine-primary-color-filled)" />
            <Text size="sm" c="var(--mantine-color-text)">
              Browse Eventum Hub...
            </Text>
          </Group>
        </Anchor>
      </Stack>
    </Stack>
  );
};
