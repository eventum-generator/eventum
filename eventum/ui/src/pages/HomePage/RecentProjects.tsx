import { Group, Paper, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconFolder } from '@tabler/icons-react';
import bytes from 'bytes';
import { formatDistanceToNow } from 'date-fns';
import { FC } from 'react';
import { Link, generatePath } from 'react-router-dom';

import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';
import { ROUTE_PATHS } from '@/routing/paths';

interface RecentProjectsProps {
  generatorDirs: GeneratorDirsExtendedInfo;
}

export const RecentProjects: FC<RecentProjectsProps> = ({ generatorDirs }) => {
  const projects = [...generatorDirs]
    .sort((a, b) => {
      if (a.last_modified !== null && b.last_modified !== null) {
        return b.last_modified - a.last_modified;
      }
      if (a.last_modified !== null) return -1;
      if (b.last_modified !== null) return 1;
      return a.name.localeCompare(b.name);
    })
    .slice(0, 8);

  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Recent projects
      </Text>
      <Paper withBorder radius="md" p="xs">
        {projects.length === 0 ? (
          <Text size="sm" c="dimmed" ta="center" py="lg">
            No projects yet - create one to get started.
          </Text>
        ) : (
          <Stack gap={2}>
            {projects.map((project) => {
              const count = project.generator_ids.length;
              const meta = [
                `${count} ${count === 1 ? 'instance' : 'instances'}`,
                project.size_in_bytes !== null
                  ? bytes(project.size_in_bytes)
                  : null,
              ]
                .filter(Boolean)
                .join(' · ');

              return (
                <UnstyledButton
                  key={project.name}
                  component={Link}
                  to={generatePath(ROUTE_PATHS.PROJECT, {
                    projectName: project.name,
                  })}
                  p="xs"
                  style={{
                    borderRadius: 'var(--mantine-radius-sm)',
                    color: 'inherit',
                  }}
                  styles={{
                    root: {
                      '&:hover': {
                        backgroundColor: 'var(--ev-hover)',
                      },
                    },
                  }}
                >
                  <Group gap="sm" justify="space-between" wrap="nowrap">
                    <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
                      <IconFolder
                        size={18}
                        color="var(--mantine-primary-color-filled)"
                        style={{ flexShrink: 0 }}
                      />
                      <Stack gap={0} style={{ minWidth: 0 }}>
                        <Text size="sm" fw={500} truncate>
                          {project.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {meta}
                        </Text>
                      </Stack>
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
              );
            })}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
};
