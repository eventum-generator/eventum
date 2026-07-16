import {
  Alert,
  Box,
  Button,
  Container,
  Group,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconLogs, IconPower, IconReload } from '@tabler/icons-react';

import {
  useRestartInstanceMutation,
  useStopInstanceMutation,
} from '@/api/hooks/useInstance';
import { streamInstanceLogs } from '@/api/routes/instance';
import { LogsModal } from '@/components/modals/LogsModal';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { CONFIRM } from '@/theme/copy';

export default function ManagementPage() {
  const restartInstance = useRestartInstanceMutation();
  const stopInstance = useStopInstanceMutation();

  function handleOnRestart() {
    restartInstance.mutate(undefined, {
      onSuccess: () => {
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
  function handleOnStop() {
    stopInstance.mutate(undefined, {
      onSuccess: () => {
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
  return (
    <Container size="xl" mb="400px">
      <Stack>
        <PageTitle title="Management" />
        <Alert
          variant="default"
          icon={<AlertIcon variant="info" />}
          title="Info"
        >
          Note, that during the restart, web interface may be unavailable for
          some time. After stopping the instance you will not be able to start
          it using web interface.
        </Alert>
        <Group grow>
          <Button
            h="60px"
            variant="default"
            onClick={() =>
              modals.open({
                title: 'Instance logs',
                children: (
                  <LogsModal
                    getWebSocket={() => streamInstanceLogs(10_048_576)}
                  />
                ),
                size: '80vw',
              })
            }
          >
            <Box mr="5px">
              <IconLogs size="16px" />
            </Box>
            Show logs
          </Button>
          <Button
            h="60px"
            variant="default"
            onClick={() =>
              modals.openConfirmModal({
                title: CONFIRM.restartInstance.title,
                children: <Text size="sm">{CONFIRM.restartInstance.body}</Text>,
                onConfirm: () => handleOnRestart(),
                labels: {
                  cancel: CONFIRM.restartInstance.cancel,
                  confirm: CONFIRM.restartInstance.confirm,
                },
              })
            }
          >
            <Box mr="5px">
              <IconReload size="16px" />
            </Box>
            Restart
          </Button>
          <Button
            h="60px"
            variant="default"
            c="var(--ev-bad)"
            onClick={() =>
              modals.openConfirmModal({
                title: CONFIRM.stopInstance.title,
                children: <Text size="sm">{CONFIRM.stopInstance.body}</Text>,
                onConfirm: () => handleOnStop(),
                labels: {
                  cancel: CONFIRM.stopInstance.cancel,
                  confirm: CONFIRM.stopInstance.confirm,
                },
              })
            }
          >
            <Box mr="5px">
              <IconPower size="16px" />
            </Box>
            Stop
          </Button>
        </Group>
      </Stack>
    </Container>
  );
}
