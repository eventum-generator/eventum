import { Grid, Group, Image, Paper, Skeleton, Stack, Text, Title } from '@mantine/core';
import { FC } from 'react';

import { InstanceInfo } from '@/api/routes/instance/schemas';

interface HeroCardProps {
  instanceInfo: InstanceInfo | undefined;
  isLoading: boolean;
  isError: boolean;
}

export const HeroCard: FC<HeroCardProps> = ({ instanceInfo, isLoading, isError }) => {
  return (
    <Paper
      withBorder
      p="xl"
      radius="md"
    >
      <Stack gap="lg">
        <Group gap="md" wrap="nowrap">
          <Image src="/logo.svg" alt="Eventum Logo" w={44} h={44} />
          <Title order={3} fw={500}>
            Eventum Studio
          </Title>
        </Group>

        {isLoading && (
          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, xs: 2 }}>
              <Skeleton h={36} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, xs: 2 }}>
              <Skeleton h={36} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, xs: 8 }}>
              <Skeleton h={36} />
            </Grid.Col>
          </Grid>
        )}
        {isError && (
          <Text size="sm" c="dimmed">
            Unable to load system info
          </Text>
        )}
        {instanceInfo && (
          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, xs: 2 }}>
              <Text size="xs" c="dimmed" fw={500}>
                Version
              </Text>
              <Text size="sm" fw={600}>
                {instanceInfo.app_version}
              </Text>
            </Grid.Col>
            <Grid.Col span={{ base: 12, xs: 2 }}>
              <Text size="xs" c="dimmed" fw={500}>
                Python
              </Text>
              <Text size="sm" fw={600}>
                {instanceInfo.python_version}
              </Text>
            </Grid.Col>
            <Grid.Col span={{ base: 12, xs: 8 }}>
              <Text size="xs" c="dimmed" fw={500}>
                Platform
              </Text>
              <Text size="sm" fw={600}>
                {instanceInfo.platform}
              </Text>
            </Grid.Col>
          </Grid>
        )}
      </Stack>
    </Paper>
  );
};
