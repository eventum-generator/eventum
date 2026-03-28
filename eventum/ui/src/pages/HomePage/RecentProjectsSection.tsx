import { Group, Paper, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconFolder } from '@tabler/icons-react';
import { formatDistanceToNow } from 'date-fns';
import { FC } from 'react';
import { generatePath, useNavigate } from 'react-router-dom';

import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';
import { ROUTE_PATHS } from '@/routing/paths';

interface RecentProjectsSectionProps {
  generatorDirs: GeneratorDirsExtendedInfo;
}

export const RecentProjectsSection: FC<RecentProjectsSectionProps> = ({
  generatorDirs,
}) => {
  const navigate = useNavigate();

  const projects = [...generatorDirs]
    .sort((a, b) => {
      if (a.last_modified !== null && b.last_modified !== null) {
        return b.last_modified - a.last_modified;
      }
      if (a.last_modified !== null) return -1;
      if (b.last_modified !== null) return 1;
      return a.name.localeCompare(b.name);
    })
    .slice(0, 10);

  if (projects.length === 0) {
    return null;
  }

  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Projects
      </Text>
      <Paper withBorder radius="md" p="xs">
        <Stack gap={2}>
          {projects.map((project) => (
            <UnstyledButton
              key={project.name}
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
                    projectName: project.name,
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
                    {project.name}
                  </Text>
                </Group>
                {project.last_modified !== null && (
                  <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
                    {formatDistanceToNow(
                      new Date(project.last_modified * 1000),
                      { addSuffix: true }
                    )}
                  </Text>
                )}
              </Group>
            </UnstyledButton>
          ))}
        </Stack>
      </Paper>
    </Stack>
  );
};
