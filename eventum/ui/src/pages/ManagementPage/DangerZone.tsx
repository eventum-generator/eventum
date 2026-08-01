import { Button, Divider, Group, Paper, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconPower, IconReload } from '@tabler/icons-react';
import { FC, ReactNode } from 'react';

import { SectionLabel } from './primitives';
import {
  useRestartInstanceMutation,
  useStopInstanceMutation,
} from '@/api/hooks/useInstance';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { CONFIRM } from '@/theme/copy';

/** Lifecycle move the user has just asked the instance to make. */
export type InstanceTransition = 'restarting' | 'stopping';

/** One control row: title + description on the left, action button on the
 *  right. */
const ControlRow: FC<{
  title: string;
  description: string;
  action: ReactNode;
}> = ({ title, description, action }) => (
  <Group justify="space-between" wrap="nowrap" gap="lg" p="md" align="center">
    <Stack gap={2} style={{ minWidth: 0 }}>
      <Text size="sm" fw={600}>
        {title}
      </Text>
      <Text size="xs" c="dimmed">
        {description}
      </Text>
    </Stack>
    {action}
  </Group>
);

interface DangerZoneProps {
  /** Called once the instance has accepted the request, so the page can
   *  show the move it is making. */
  onTransition: (transition: InstanceTransition) => void;
}

export const DangerZone: FC<DangerZoneProps> = ({ onTransition }) => {
  const restartInstance = useRestartInstanceMutation();
  const stopInstance = useStopInstanceMutation();

  function handleRestart() {
    restartInstance.mutate(undefined, {
      onSuccess: () => {
        onTransition('restarting');
        notifications.show({
          title: 'Info',
          message:
            'Restarting the instance. Service may be unavailable for some time',
          color: 'blue',
        });
      },
      onError: (error) => {
        notifications.show({
          title: 'Error',
          message: (
            <>
              Failed to restart instance.{' '}
              <ShowErrorDetailsAnchor error={error} />
            </>
          ),
          color: 'red',
        });
      },
    });
  }

  function handleStop() {
    stopInstance.mutate(undefined, {
      onSuccess: () => {
        onTransition('stopping');
        notifications.show({
          title: 'Info',
          message: 'Stopping the instance',
          color: 'blue',
        });
      },
      onError: (error) => {
        notifications.show({
          title: 'Error',
          message: (
            <>
              Failed to stop instance. <ShowErrorDetailsAnchor error={error} />
            </>
          ),
          color: 'red',
        });
      },
    });
  }

  function confirmRestart() {
    modals.openConfirmModal({
      title: CONFIRM.restartInstance.title,
      children: <Text size="sm">{CONFIRM.restartInstance.body}</Text>,
      onConfirm: handleRestart,
      labels: {
        cancel: CONFIRM.restartInstance.cancel,
        confirm: CONFIRM.restartInstance.confirm,
      },
    });
  }

  function confirmStop() {
    modals.openConfirmModal({
      title: CONFIRM.stopInstance.title,
      children: <Text size="sm">{CONFIRM.stopInstance.body}</Text>,
      onConfirm: handleStop,
      labels: {
        cancel: CONFIRM.stopInstance.cancel,
        confirm: CONFIRM.stopInstance.confirm,
      },
    });
  }

  return (
    <Stack gap="xs">
      <SectionLabel color="var(--mantine-color-red-text)">
        Danger zone
      </SectionLabel>
      <Paper withBorder p={0} style={{ overflow: 'hidden' }}>
        <ControlRow
          title="Restart instance"
          description="Stops and starts the instance. The web interface may be briefly unavailable while it restarts."
          action={
            <Button
              variant="default"
              leftSection={<IconReload size={16} />}
              onClick={confirmRestart}
              loading={restartInstance.isPending}
            >
              Restart
            </Button>
          }
        />
        <Divider />
        <ControlRow
          title="Stop instance"
          description="Stops the instance. You will not be able to start it again from the web interface."
          action={
            <Button
              variant="default"
              color="red"
              leftSection={<IconPower size={16} />}
              onClick={confirmStop}
              loading={stopInstance.isPending}
            >
              Stop
            </Button>
          }
        />
      </Paper>
    </Stack>
  );
};
