import { Alert, Center, Container, Loader, Stack } from '@mantine/core';
import { ReactFlowProvider } from '@xyflow/react';
import { FC, useEffect, useRef } from 'react';

import { PipelineGraph } from './PipelineGraph';
import { SummaryBar } from './SummaryBar';
import { APIError } from '@/api/errors';
import { useGeneratorStats } from '@/api/hooks/useGenerators';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface InstanceMetricsProps {
  instanceId: string;
}

/**
 * Live per-plugin metrics for one instance: a summary bar over a pipeline
 * graph, polled while mounted. Shared by the instances-table quick-action
 * modal and the instance page Metrics tab.
 */
export const InstanceMetrics: FC<InstanceMetricsProps> = ({ instanceId }) => {
  const {
    data: stats,
    isLoading: isStatsLoading,
    isSuccess: isStatsSuccess,
    isError: isStatsError,
    error: statsError,
    refetch: refetchStats,
  } = useGeneratorStats(instanceId);

  const stoppedRef = useRef(false);

  useEffect(() => {
    const timeout = setInterval(() => {
      if (!stoppedRef.current) {
        void refetchStats();
      }
    }, 3000);

    return () => {
      clearInterval(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (
      isStatsError &&
      statsError instanceof APIError &&
      statsError.response?.status === 400
    ) {
      stoppedRef.current = true;
    }
  }, [isStatsError, statsError]);

  if (isStatsLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isStatsError) {
    if (statsError instanceof APIError && statsError.response?.status === 400) {
      return (
        <Container size="md">
          <Alert
            variant="default"
            icon={<AlertIcon variant="info" />}
            title="Instance is not running"
          >
            The generator has stopped. Start it again to see live metrics.
          </Alert>
        </Container>
      );
    }

    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
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
