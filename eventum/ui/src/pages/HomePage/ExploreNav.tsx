import { Group, Paper, SimpleGrid, Stack, Text } from '@mantine/core';
import {
  Icon,
  IconFolder,
  IconPlayerPlay,
  IconTransform,
} from '@tabler/icons-react';
import { FC } from 'react';
import { Link } from 'react-router-dom';

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
  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Explore
      </Text>
      <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="md">
        {TILES.map((tile) => (
          <Paper
            key={tile.title}
            component={Link}
            to={tile.path}
            withBorder
            radius="md"
            p="md"
            className="ev-tile-button"
            style={{
              cursor: 'pointer',
              transition: 'border-color 150ms ease',
              color: 'inherit',
              textDecoration: 'none',
            }}
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
