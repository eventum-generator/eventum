import { Group, Paper, SimpleGrid, Stack, Text } from '@mantine/core';
import {
  Icon,
  IconFolder,
  IconPlayerPlay,
  IconTransform,
} from '@tabler/icons-react';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import { ROUTE_PATHS } from '@/routing/paths';

const TILES: { icon: Icon; title: string; caption: string; path: string }[] = [
  {
    icon: IconFolder,
    title: 'Projects',
    caption: 'Design generator projects',
    path: ROUTE_PATHS.PROJECTS,
  },
  {
    icon: IconPlayerPlay,
    title: 'Instances',
    caption: 'Manage generator instances',
    path: ROUTE_PATHS.INSTANCES,
  },
  {
    icon: IconTransform,
    title: 'Scenarios',
    caption: 'Build multi-generator scenarios',
    path: ROUTE_PATHS.SCENARIOS,
  },
];

export const ExploreNav: FC = () => {
  const navigate = useNavigate();

  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Explore
      </Text>
      <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="md">
        {TILES.map((tile) => (
          <Paper
            key={tile.title}
            withBorder
            radius="md"
            p="md"
            style={{ cursor: 'pointer', transition: 'border-color 150ms ease' }}
            styles={{
              root: {
                '&:hover': {
                  borderColor: 'var(--mantine-primary-color-filled)',
                },
              },
            }}
            onClick={() => void navigate(tile.path)}
          >
            <Group gap="sm" wrap="nowrap">
              <tile.icon
                size={20}
                stroke={1.5}
                color="var(--mantine-primary-color-filled)"
                style={{ flexShrink: 0 }}
              />
              <Stack gap={0} style={{ minWidth: 0 }}>
                <Text size="sm" fw={600}>
                  {tile.title}
                </Text>
                <Text size="xs" c="dimmed">
                  {tile.caption}
                </Text>
              </Stack>
            </Group>
          </Paper>
        ))}
      </SimpleGrid>
    </Stack>
  );
};
