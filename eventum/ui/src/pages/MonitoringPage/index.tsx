import {
  Alert,
  Container,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
} from '@mantine/core';
import { ReactNode, useEffect, useMemo, useState } from 'react';

import { ErrorsChart } from './ErrorsChart';
import { InstancesSection } from './InstancesSection';
import { NoRunningGenerators } from './NoRunningGenerators';
import { ResourceTiles } from './ResourceTiles';
import { StateStrip } from './StateStrip';
import { ThroughputChart } from './ThroughputChart';
import { WindowSelector } from './WindowSelector';
import { MAX_POINTS, instanceUsageRows, useMetricsHistory } from './history';
import { aggregateFlow } from './metrics';
import { useRunningGeneratorsStats } from '@/api/hooks/useGenerators';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { AlertIcon } from '@/components/ui/AlertIcon';
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
  const {
    data: generatorsStats,
    dataUpdatedAt: statsUpdatedAt,
    isLoading: isStatsLoading,
    refetch: refetchStats,
  } = useRunningGeneratorsStats();

  const [points, setPoints] = useState(MAX_POINTS);

  useEffect(() => {
    const interval = setInterval(() => {
      void refetchInfo();
      void refetchStats();
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stats = generatorsStats ?? [];

  const { resources, flow, load, usage, current } = useMetricsHistory({
    instanceInfo,
    instanceUpdatedAt,
    stats,
    statsUpdatedAt,
  });

  const flowAgg = aggregateFlow(stats);
  const rows = useMemo(() => instanceUsageRows(usage), [usage]);

  let liveSection: ReactNode;
  if (isStatsLoading) {
    liveSection = <Skeleton h={220} radius="lg" />;
  } else if (stats.length === 0) {
    liveSection = <NoRunningGenerators />;
  } else {
    liveSection = (
      <>
        <StateStrip
          flow={flowAgg}
          current={current}
          rows={rows}
          instances={stats.length}
        />

        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
          <ThroughputChart
            flow={flow}
            inputEps={current.inputEps}
            outputEps={current.outputEps}
            points={points}
            height={150}
          />
          <ErrorsChart flow={flow} points={points} height={150} />
        </SimpleGrid>
      </>
    );
  }

  return (
    <Container size="100%">
      <Stack gap="md">
        <Group justify="space-between" align="center" wrap="wrap" gap="md">
          <PageTitle title="Monitoring" />
          <WindowSelector points={points} onChange={setPoints} />
        </Group>

        {isInfoError && (
          <Alert
            variant="default"
            icon={<AlertIcon variant="error" />}
            title="Failed to load instance info"
          >
            {infoError.message}
            <ShowErrorDetailsAnchor error={infoError} prependDot />
          </Alert>
        )}

        {liveSection}

        {isInfoLoading && !instanceInfo ? (
          <Skeleton h={160} radius="lg" />
        ) : (
          instanceInfo && (
            <ResourceTiles
              info={instanceInfo}
              resources={resources}
              current={current}
              points={points}
            />
          )
        )}

        {stats.length > 0 && (
          <InstancesSection
            rows={rows}
            load={load}
            flow={flow}
            stats={stats}
            points={points}
          />
        )}
      </Stack>
    </Container>
  );
}
