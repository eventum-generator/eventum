import { Alert, Center, Container, Group, Loader, Stack } from '@mantine/core';

import { DangerZone } from './DangerZone';
import { IdentityGrid } from './IdentityGrid';
import { LogsPanel } from './LogsPanel';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { StatusChip } from '@/components/ui/StatusChip';

export default function ManagementPage() {
  const {
    data: info,
    isLoading,
    isError,
    error,
  } = useInstanceInfo({ refetchInterval: 5000 });

  if (isLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isError) {
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
          <StatusChip variant="good">Running</StatusChip>
        </Group>

        <IdentityGrid info={info} />
        <LogsPanel />
        <DangerZone />
      </Stack>
    </Container>
  );
}
