import {
  Alert,
  Box,
  Container,
  Grid,
  Group,
  Indicator,
  MantineColor,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { useEffect } from 'react';

import { InstancesStatsPanel } from './InstancesStatsPanel';
import { InstancesStatusesPanel } from './InstancesStatusesPanel';
import { LastInstancesListPanel } from './LastInstancesListPanel';
import { PerformancePanel } from './PerformancePanel';
import {
  useGenerators,
  useRunningGeneratorsStats,
} from '@/api/hooks/useGenerators';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function OverviewPage() {
  const {
    data: instanceInfo,
    isLoading: isInstanceInfoLoading,
    isError: isInstanceInfoError,
    isSuccess: isInstanceInfoSuccess,
    error: instanceInfoError,
    refetch: refetchInstanceInfo,
  } = useInstanceInfo();

  const {
    data: generators,
    isLoading: isGeneratorsLoading,
    isError: isGeneratorsError,
    error: generatorsError,
    isSuccess: isGeneratorsSuccess,
    refetch: refetchGenerators,
  } = useGenerators();

  const {
    data: generatorsStats,
    isLoading: isGeneratorsStatsLoading,
    isError: isGeneratorsStatsError,
    error: generatorsStatsError,
    isSuccess: isGeneratorsStatsSuccess,
    refetch: refetchGeneratorsStats,
  } = useRunningGeneratorsStats();

  useEffect(() => {
    const timeout = setInterval(() => {
      void refetchInstanceInfo();
      void refetchGenerators();
      void refetchGeneratorsStats();
    }, 10_000);

    return () => clearInterval(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  let indicatorText = 'Stale';
  let indicatorColor: MantineColor = 'gray.6';

  if (isInstanceInfoSuccess) {
    indicatorText = 'Connected';
    indicatorColor = 'green.6';
  } else if (isInstanceInfoLoading) {
    indicatorText = 'Updating ...';
    indicatorColor = 'yellow.6';
  } else if (isInstanceInfoError) {
    indicatorText = 'Disconnected';
    indicatorColor = 'red.6';
  }

  return (
    <Container size="100%">
      <Stack>
        <Group justify="space-between">
          <Title order={2} fw="500">
            Overview
          </Title>

          <Group wrap="nowrap" gap="12px">
            <Indicator
              color={indicatorColor}
              position="middle-center"
              size="8px"
              processing
            />
            <Text c="gray.6" size="sm">
              {indicatorText}
            </Text>
          </Group>
        </Group>

        <Grid columns={12}>
          <Grid.Col span={9}>
            <Stack>
              <Box>
                {isInstanceInfoError && (
                  <Alert
                    variant="default"
                    icon={
                      <Box c="red" component={IconAlertSquareRounded}></Box>
                    }
                    title="Failed to load app instance info"
                  >
                    {instanceInfoError.message}
                    <ShowErrorDetailsAnchor
                      error={instanceInfoError}
                      prependDot
                    />
                  </Alert>
                )}
                {isInstanceInfoLoading && <Skeleton h="280px" />}
                {isInstanceInfoSuccess && (
                  <PerformancePanel instanceInfo={instanceInfo} />
                )}
              </Box>

              <Box>
                {isGeneratorsStatsError && (
                  <Alert
                    variant="default"
                    icon={
                      <Box c="red" component={IconAlertSquareRounded}></Box>
                    }
                    title="Failed to load stats of generator instances"
                  >
                    {generatorsStatsError.message}
                    <ShowErrorDetailsAnchor
                      error={generatorsStatsError}
                      prependDot
                    />
                  </Alert>
                )}
                {isGeneratorsStatsLoading && <Skeleton h="280px" />}
                {isGeneratorsStatsSuccess && (
                  <InstancesStatsPanel generatorsStats={generatorsStats} />
                )}
              </Box>
            </Stack>
          </Grid.Col>
          <Grid.Col span={3}>
            {isGeneratorsError && (
              <Alert
                variant="default"
                icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
                title="Failed to load statuses of generator instances"
              >
                {generatorsError.message}
                <ShowErrorDetailsAnchor error={generatorsError} prependDot />
              </Alert>
            )}
            {isGeneratorsLoading && <Skeleton h="85vh" />}
            {isGeneratorsSuccess && (
              <Stack>
                <InstancesStatusesPanel generators={generators} />
                <LastInstancesListPanel generators={generators} />
              </Stack>
            )}
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  );
}
