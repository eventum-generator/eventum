import { Alert, Container, Group, Skeleton, Stack } from '@mantine/core';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { ReactNode, useEffect } from 'react';

import { ErrorsChart } from './ErrorsChart';
import { FleetStatus } from './FleetStatus';
import { InstanceLoad } from './InstanceLoad';
import { NoRunningGenerators } from './NoRunningGenerators';
import { PipelineFlow } from './PipelineFlow';
import { ResourceTiles } from './ResourceTiles';
import { ThroughputChart } from './ThroughputChart';
import { useMetricsHistory } from './history';
import { aggregateFlow } from './metrics';
import {
  useGenerators,
  useRunningGeneratorsStats,
} from '@/api/hooks/useGenerators';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function MonitoringPage() {
  const {
    data: instanceInfo,
    dataUpdatedAt: instanceUpdatedAt,
    isError: isInfoError,
    error: infoError,
    isLoading: isInfoLoading,
    refetch: refetchInfo,
  } = useInstanceInfo();
  const { data: generators, refetch: refetchGenerators } = useGenerators();
  const {
    data: generatorsStats,
    dataUpdatedAt: statsUpdatedAt,
    isLoading: isStatsLoading,
    refetch: refetchStats,
  } = useRunningGeneratorsStats();

  useEffect(() => {
    const interval = setInterval(() => {
      void refetchInfo();
      void refetchGenerators();
      void refetchStats();
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const gens = generators ?? [];
  const stats = generatorsStats ?? [];

  const { resources, flow, load, current } = useMetricsHistory({
    instanceInfo,
    instanceUpdatedAt,
    stats,
    statsUpdatedAt,
  });

  const flowAgg = aggregateFlow(stats);
  const inputPlugins = stats.reduce((n, s) => n + s.input.length, 0);

  let liveSection: ReactNode;
  if (isStatsLoading) {
    liveSection = <Skeleton h={220} radius="md" />;
  } else if (stats.length === 0) {
    liveSection = <NoRunningGenerators />;
  } else {
    liveSection = (
      <>
        <PipelineFlow flow={flowAgg} inputPlugins={inputPlugins} />

        <ThroughputChart
          flow={flow}
          inputEps={current.inputEps}
          outputEps={current.outputEps}
        />

        {current.failing && <ErrorsChart flow={flow} />}

        <InstanceLoad load={load} />
      </>
    );
  }

  return (
    <Container size="100%">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <PageTitle title="Monitoring" />
          <FleetStatus generators={gens} />
        </Group>

        {isInfoError && (
          <Alert
            variant="default"
            color="red"
            icon={<IconAlertSquareRounded />}
            title="Failed to load instance info"
          >
            {infoError.message}
            <ShowErrorDetailsAnchor error={infoError} prependDot />
          </Alert>
        )}

        {liveSection}

        {isInfoLoading && !instanceInfo ? (
          <Skeleton h={160} radius="md" />
        ) : (
          instanceInfo && (
            <ResourceTiles
              info={instanceInfo}
              resources={resources}
              current={current}
            />
          )
        )}
      </Stack>
    </Container>
  );
}
