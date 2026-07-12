import {
  ActionIcon,
  Anchor,
  Button,
  Group,
  Menu,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconArrowLeft,
  IconCopy,
  IconDeviceFloppy,
  IconDotsVertical,
  IconFolder,
  IconPlayerPlayFilled,
  IconPlayerStopFilled,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react';
import { FC } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { CloneInstanceModal } from '../InstancesPage/CloneInstanceModal';
import { Dot } from './primitives';
import { useInstanceActions } from './useInstanceActions';
import {
  useDeleteGeneratorMutation,
  useGenerators,
} from '@/api/hooks/useGenerators';
import { useDeleteGeneratorFromStartupMutation } from '@/api/hooks/useStartup';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { StatusPill } from '@/components/ui/StatusPill';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface InstanceHeaderProps {
  instanceId: string;
  status: GeneratorStatus;
  projectName: string;
  liveMode: boolean;
  autostart: boolean;
  isDirty: boolean;
  isSaving: boolean;
  onSave: () => void;
  onBack: () => void;
}

export const InstanceHeader: FC<InstanceHeaderProps> = ({
  instanceId,
  status,
  projectName,
  liveMode,
  autostart,
  isDirty,
  isSaving,
  onSave,
  onBack,
}) => {
  const navigate = useNavigate();
  const { data: generators } = useGenerators();
  const { handleStart, handleStop, handleRestart, isStarting, isStopping } =
    useInstanceActions(instanceId);

  const deleteGenerator = useDeleteGeneratorMutation();
  const deleteGeneratorFromStartup = useDeleteGeneratorFromStartupMutation();

  const isActive =
    status.is_running || status.is_initializing || status.is_stopping;

  function handleClone() {
    modals.open({
      title: 'Clone instance',
      children: (
        <CloneInstanceModal
          sourceInstanceId={instanceId}
          existingInstanceIds={(generators ?? []).map((g) => g.id)}
        />
      ),
      size: 'lg',
    });
  }

  function handleDelete() {
    deleteGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () => {
          deleteGeneratorFromStartup.mutate(
            { id: instanceId },
            {
              onSuccess: () => {
                showSuccessNotification('Success', 'Instance is deleted');
                void navigate(ROUTE_PATHS.INSTANCES);
              },
              onError: (error) =>
                showErrorNotification(
                  'Failed to delete instance definition from startup',
                  error
                ),
            }
          );
        },
        onError: (error) =>
          showErrorNotification('Failed to delete instance', error),
      }
    );
  }

  function confirmDelete() {
    modals.openConfirmModal({
      title: 'Deleting instance',
      children: (
        <Text size="sm">
          Instance <b>{instanceId}</b> will be deleted. Do you want to continue?
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Confirm' },
      confirmProps: { color: 'red' },
      onConfirm: handleDelete,
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
            <Anchor
              component={Link}
              to={`${ROUTE_PATHS.PROJECTS}/${projectName}`}
              c="dimmed"
              underline="hover"
            >
              <Group gap={6} wrap="nowrap" align="center">
                <IconFolder size={15} style={{ flexShrink: 0 }} />
                <Text size="sm">{projectName}</Text>
              </Group>
            </Anchor>
            <Dot />
            <Text size="sm" c="dimmed">
              {liveMode ? 'Live mode' : 'Sample mode'}
            </Text>
            {autostart && (
              <>
                <Dot />
                <Text size="sm" c="dimmed">
                  Autostart
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
                onClick={handleRestart}
                loading={isStopping || isStarting}
              >
                Restart
              </Button>
            )}
            <Button
              variant="default"
              leftSection={
                <IconPlayerStopFilled size={15} color="var(--ev-bad)" />
              }
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
            leftSection={
              <IconPlayerPlayFilled size={15} color="var(--ev-good)" />
            }
            onClick={handleStart}
            loading={isStarting}
          >
            Start
          </Button>
        )}

        <Menu shadow="md" width={170} position="bottom-end">
          <Menu.Target>
            <ActionIcon variant="default" size="lg" title="More actions">
              <IconDotsVertical size={18} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              leftSection={<IconCopy size={14} />}
              onClick={handleClone}
            >
              Clone
            </Menu.Item>
            <Menu.Divider />
            <Menu.Item
              color="red"
              leftSection={<IconTrash size={14} />}
              onClick={confirmDelete}
              disabled={isActive}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    </Group>
  );
};
