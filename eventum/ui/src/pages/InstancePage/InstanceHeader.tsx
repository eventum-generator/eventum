import { ActionIcon, Button, Group, Text, Title } from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconArrowLeft,
  IconDeviceFloppy,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
} from '@tabler/icons-react';
import { FC } from 'react';

import { LiveUptime } from './primitives';
import { useInstanceActions } from './useInstanceActions';
import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { StatusPill } from '@/components/ui/StatusPill';

interface InstanceHeaderProps {
  instanceId: string;
  status: GeneratorStatus;
  isDirty: boolean;
  isSaving: boolean;
  onSave: () => void;
  onBack: () => void;
}

export const InstanceHeader: FC<InstanceHeaderProps> = ({
  instanceId,
  status,
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
    // The row wraps rather than compressing: held on one line, the actions
    // keep their width and the title is squeezed to nothing instead.
    <Group justify="space-between" align="center" gap="md">
      <Group
        gap="sm"
        align="center"
        wrap="nowrap"
        style={{ minWidth: 0, flex: '1 1 auto' }}
      >
        <ActionIcon
          variant="subtle"
          size="lg"
          onClick={onBack}
          title="Back to instances"
        >
          <IconArrowLeft size={20} color="var(--mantine-color-dimmed)" />
        </ActionIcon>
        <Title
          order={2}
          fz="1.5rem"
          fw={650}
          title={instanceId}
          style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {instanceId}
        </Title>
        <StatusPill status={status} />
        {status.is_running && startTime && (
          <Text
            size="sm"
            c="dimmed"
            ff="monospace"
            style={{ fontVariantNumeric: 'tabular-nums', flexShrink: 0 }}
          >
            up <LiveUptime startTime={Date.parse(startTime)} />
          </Text>
        )}
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
