import {
  Alert,
  Box,
  Center,
  Container,
  Loader,
  Stack,
} from '@mantine/core';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { ReactFlowProvider } from '@xyflow/react';
import { FC, useEffect } from 'react';

import { PipelineGraph } from './metrics/PipelineGraph';
import { SummaryBar } from './metrics/SummaryBar';
import { useGeneratorStats } from '@/api/hooks/useGenerators';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface MetricsModalProps {
  instanceId: string;
}

export const MetricsModal: FC<MetricsModalProps> = ({ instanceId }) => {
  const {
    data: stats,
    isLoading: isStatsLoading,
    isSuccess: isStatsSuccess,
    isError: isStatsError,
    error: statsError,
    refetch: refetchStats,
  } = useGeneratorStats(instanceId);

  useEffect(() => {
    const timeout = setInterval(() => {
      void refetchStats();
    }, 3000);

    return () => {
      clearInterval(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isStatsLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isStatsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load instance stats"
        >
          {statsError.message}
          <ShowErrorDetailsAnchor error={statsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isStatsSuccess) {
    return (
      <Stack gap="md">
        <SummaryBar stats={stats} />
        <ReactFlowProvider>
          <PipelineGraph stats={stats} />
        </ReactFlowProvider>
      </Stack>
    );
  }

  return null;
};
