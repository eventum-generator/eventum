import { Alert, Center, Container, Group, Loader, Stack } from '@mantine/core';
import { useEffect, useState } from 'react';

import { DangerZone, InstanceTransition } from './DangerZone';
import { IdentityGrid } from './IdentityGrid';
import { LogsPanel } from './LogsPanel';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { StatusChip } from '@/components/ui/StatusChip';

const TRANSITION_LABEL: Record<InstanceTransition, string> = {
  restarting: 'Restarting',
  stopping: 'Stopping',
};

/** How long the page holds still before loading afresh. */
const RELOAD_DELAY_MS = 3000;

export default function ManagementPage() {
  const {
    data: info,
    isLoading,
    isError,
    error,
  } = useInstanceInfo({ refetchInterval: 5000 });

  const [transition, setTransition] = useState<InstanceTransition | null>(null);

  useEffect(() => {
    if (transition === null) return;

    // Everything the page holds is cut with the instance - the log stream
    // above all - so it is loaded afresh rather than pieced back together.
    // Whatever the instance is by then, the page shows it: running again
    // after a restart, unreachable after a stop.
    const timer = setTimeout(
      () => globalThis.location.reload(),
      RELOAD_DELAY_MS
    );

    return () => clearTimeout(timer);
  }, [transition]);

  if (isLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  // The polls that fail while the instance is on the move are the move
  // itself - report a fault only when nothing was asked of it.
  if (isError && transition === null) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to get instance information"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </Alert>
      </Container>
    );
  }

  if (!info) {
    return null;
  }

  return (
    <Container size="100%">
      <Stack gap="lg">
        <Group gap="sm" align="center" wrap="nowrap">
          <PageTitle title="Management" />
          {transition === null ? (
            <StatusChip variant="good">Running</StatusChip>
          ) : (
            <StatusChip variant="warn" processing>
              {TRANSITION_LABEL[transition]}
            </StatusChip>
          )}
        </Group>

        <IdentityGrid info={info} />
        <LogsPanel />
        <DangerZone onTransition={setTransition} />
      </Stack>
    </Container>
  );
}
