import { ActionIcon, Button, Group, Stack, Text, Title } from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconArrowLeft,
  IconDeviceFloppy,
  IconFolder,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
} from '@tabler/icons-react';
import { formatDistanceToNow } from 'date-fns';
import { FC } from 'react';

import { formatUptime } from './format';
import { Dot } from './primitives';
import { useInstanceActions } from './useInstanceActions';
import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { RecordNameLink } from '@/components/ui/RecordNameLink';
import { StatusPill } from '@/components/ui/StatusPill';
import { ROUTE_PATHS } from '@/routing/paths';

interface InstanceHeaderProps {
  instanceId: string;
  status: GeneratorStatus;
  projectName: string;
  isDirty: boolean;
  isSaving: boolean;
  onSave: () => void;
  onBack: () => void;
}

export const InstanceHeader: FC<InstanceHeaderProps> = ({
  instanceId,
  status,
  projectName,
  isDirty,
  isSaving,
  onSave,
  onBack,
}) => {
  const { data: generators } = useGenerators();
  const startTime = generators?.find((g) => g.id === instanceId)?.start_time;
  const { handleStart, handleStop, handleRestart, isStarting, isStopping } =
    useInstanceActions(instanceId);

  const isActive =
    status.is_running || status.is_initializing || status.is_stopping;

  let runMeta: string | null = null;
  if (startTime) {
    runMeta = status.is_running
      ? `Up ${formatUptime((Date.now() - Date.parse(startTime)) / 1000)}`
      : `Last run ${formatDistanceToNow(Date.parse(startTime), { addSuffix: true })}`;
  }

  function confirmRestart() {
    modals.openConfirmModal({
      title: 'Restart instance',
      children: (
        <Text size="sm">
          Instance <b>{instanceId}</b> will be stopped and started again. Do you
          want to continue?
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Restart' },
      onConfirm: handleRestart,
    });
  }

  return (
    <Group justify="space-between" align="flex-start" wrap="nowrap" gap="md">
      <Group gap="sm" align="flex-start" wrap="nowrap" style={{ minWidth: 0 }}>
        <ActionIcon
          variant="subtle"
          color="gray"
          size="lg"
          onClick={onBack}
          title="Back to instances"
          mt={2}
        >
          <IconArrowLeft size={20} />
        </ActionIcon>
        <Stack gap={6} style={{ minWidth: 0 }}>
          <Group gap="sm" align="center" wrap="nowrap">
            <Title
              order={2}
              fz="1.5rem"
              fw={650}
              style={{ wordBreak: 'break-all' }}
            >
              {instanceId}
            </Title>
            <StatusPill status={status} />
          </Group>
          <Group gap={10} align="center" wrap="wrap">
            <RecordNameLink to={`${ROUTE_PATHS.PROJECTS}/${projectName}`}>
              <Group gap={6} wrap="nowrap" align="center">
                <IconFolder size={15} style={{ flexShrink: 0 }} />
                <Text size="sm">{projectName}</Text>
              </Group>
            </RecordNameLink>
            {runMeta && (
              <>
                <Dot />
                <Text size="sm" c="dimmed">
                  {runMeta}
                </Text>
              </>
            )}
          </Group>
        </Stack>
      </Group>

      <Group gap="xs" wrap="nowrap">
        {isDirty && (
          <Button
            leftSection={<IconDeviceFloppy size={16} />}
            onClick={onSave}
            loading={isSaving}
          >
            Save
          </Button>
        )}

        {isActive ? (
          <>
            {status.is_running && (
              <Button
                variant="default"
                leftSection={<IconRefresh size={16} />}
                onClick={confirmRestart}
                loading={isStopping || isStarting}
              >
                Restart
              </Button>
            )}
            <Button
              variant="default"
              leftSection={<IconPlayerStop size={16} />}
              onClick={handleStop}
              loading={isStopping}
              disabled={!status.is_running}
            >
              Stop
            </Button>
          </>
        ) : (
          <Button
            variant="default"
            leftSection={<IconPlayerPlay size={16} />}
            onClick={handleStart}
            loading={isStarting}
          >
            Start
          </Button>
        )}
      </Group>
    </Group>
  );
};
