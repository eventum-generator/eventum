import { Grid, Group, Image, Paper, Skeleton, Stack, Text, Title } from '@mantine/core';
import { FC } from 'react';

import { InstanceInfo } from '@/api/routes/instance/schemas';

interface HeroCardProps {
  instanceInfo: InstanceInfo | undefined;
  isLoading: boolean;
}

export const HeroCard: FC<HeroCardProps> = ({ instanceInfo, isLoading }) => {
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
            {Array.from({ length: 3 }).map((_, i) => (
              <Grid.Col key={i} span={4}>
                <Skeleton h={36} />
              </Grid.Col>
            ))}
          </Grid>
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
