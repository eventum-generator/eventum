import {
  Box,
  Flex,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { FC } from 'react';

import { InstanceInfo } from '@/api/routes/instance/schemas';

interface HeroCardProps {
  instanceInfo: InstanceInfo | undefined;
  isLoading: boolean;
  isError: boolean;
}

export const HeroCard: FC<HeroCardProps> = ({
  instanceInfo,
  isLoading,
  isError,
}) => {
  return (
    <Paper withBorder p="xl">
      <Flex
        direction={{ base: 'column', sm: 'row' }}
        justify="space-between"
        align={{ base: 'flex-start', sm: 'center' }}
        gap="lg"
      >
        <Group gap="md" wrap="nowrap">
          <Box
            style={(theme) => ({
              width: 48,
              height: 48,
              borderRadius: theme.radius.md,
              background: `linear-gradient(${theme.defaultGradient.deg}deg, ${theme.defaultGradient.from}, ${theme.defaultGradient.to})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            })}
          >
            <Text size="xl" fw={700} c="white">
              E
            </Text>
          </Box>
          <Stack gap={4}>
            <Title order={3}>Eventum Studio</Title>
            <Text size="sm" c="dimmed">
              Synthetic Event Generation Platform
            </Text>
          </Stack>
        </Group>

        <Box>
          {isLoading && (
            <SimpleGrid cols={2} spacing="xs" verticalSpacing="xs">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} h={20} w={100} />
              ))}
            </SimpleGrid>
          )}
          {isError && (
            <Text size="sm" c="dimmed">
              Unable to load system info
            </Text>
          )}
          {instanceInfo && (
            <SimpleGrid cols={2} spacing="xs" verticalSpacing="xs">
              <Text size="xs" c="dimmed">
                Version
              </Text>
              <Text size="sm">{instanceInfo.app_version}</Text>
              <Text size="xs" c="dimmed">
                Hostname
              </Text>
              <Text size="sm">{instanceInfo.host_name}</Text>
              <Text size="xs" c="dimmed">
                Platform
              </Text>
              <Text size="sm">{instanceInfo.platform}</Text>
              <Text size="xs" c="dimmed">
                Python
              </Text>
              <Text size="sm">{instanceInfo.python_version}</Text>
            </SimpleGrid>
          )}
        </Box>
      </Flex>
    </Paper>
  );
};
