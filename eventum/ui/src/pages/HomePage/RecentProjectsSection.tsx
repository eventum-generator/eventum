import { Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconFolder } from '@tabler/icons-react';
import { FC } from 'react';
import { generatePath, useNavigate } from 'react-router-dom';

import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { ROUTE_PATHS } from '@/routing/paths';

interface RecentProjectsSectionProps {
  generators: GeneratorsInfo;
}

export const RecentProjectsSection: FC<RecentProjectsSectionProps> = ({
  generators,
}) => {
  const navigate = useNavigate();

  const recentProjects = [...generators]
    .filter((g) => g.start_time !== null)
    .sort(
      (a, b) =>
        new Date(b.start_time!).getTime() - new Date(a.start_time!).getTime()
    )
    .slice(0, 5);

  if (recentProjects.length === 0) {
    return null;
  }

  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Recent Projects
      </Text>
      <Stack gap={4}>
        {recentProjects.map((project) => (
          <UnstyledButton
            key={project.id}
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
              void navigate(
                generatePath(ROUTE_PATHS.PROJECT, {
                  projectName: project.id,
                })
              )
            }
          >
            <Group gap="xs" justify="space-between" wrap="nowrap">
              <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                <IconFolder
                  size={18}
                  color="var(--mantine-primary-color-filled)"
                  style={{ flexShrink: 0 }}
                />
                <Text size="sm" truncate>
                  {project.id}
                </Text>
              </Group>
              <Text
                size="xs"
                c="dimmed"
                truncate
                style={{ flexShrink: 1, minWidth: 0 }}
              >
                {project.path}
              </Text>
            </Group>
          </UnstyledButton>
        ))}
      </Stack>
    </Stack>
  );
};
