import {
  ActionIcon,
  Box,
  Group,
  Indicator,
  Paper,
  Text,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconExternalLink,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { dirname } from 'pathe';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  useStartGeneratorMutation,
  useStopGeneratorMutation,
} from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export interface GeneratorCardProps {
  generatorId: string;
  generatorPath: string;
  status?: GeneratorStatus;
  onRemove: () => void;
}

export const GeneratorCard: FC<GeneratorCardProps> = ({
  generatorId,
  generatorPath,
  status,
  onRemove,
}) => {
  const navigate = useNavigate();

  const startMutation = useStartGeneratorMutation();
  const stopMutation = useStopGeneratorMutation();

  const projectName = dirname(generatorPath);
  const isActive = status?.is_running ?? false;
  const isTransitioning =
    (status?.is_initializing ?? false) || (status?.is_stopping ?? false);
  const statusInfo = status
    ? describeInstanceStatus(status)
    : { text: 'Inactive', color: 'gray.6' as const, processing: false };

  function handleStart() {
    startMutation.mutate(
      { id: generatorId },
      {
        onSuccess: () =>
          notifications.show({
            title: 'Success',
            message: `Instance "${generatorId}" started`,
            color: 'green',
          }),
        onError: (error) =>
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to start instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          }),
      }
    );
  }

  function handleStop() {
    stopMutation.mutate(
      { id: generatorId },
      {
        onSuccess: () =>
          notifications.show({
            title: 'Success',
            message: `Instance "${generatorId}" stopped`,
            color: 'green',
          }),
        onError: (error) =>
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to stop instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          }),
      }
    );
  }

  return (
    <Paper withBorder p="xs">
      <Group justify="space-between" align="center" wrap="nowrap">
        <Group gap="sm" align="center" wrap="nowrap" style={{ minWidth: 0 }}>
          <Tooltip label={statusInfo.text} withArrow>
            <Box style={{ lineHeight: 0 }}>
              <Indicator
                color={statusInfo.color}
                size={8}
                position="middle-center"
                processing={statusInfo.processing}
              />
            </Box>
          </Tooltip>
          <Text size="sm" fw={500} truncate>
            {generatorId}
          </Text>
          <Text size="xs" c="dimmed" truncate>
            {projectName}
          </Text>
        </Group>

        <Group gap={4} wrap="nowrap">
          {isActive || isTransitioning ? (
            <Tooltip label="Stop" withArrow>
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={handleStop}
                disabled={stopMutation.isPending}
              >
                <IconPlayerStop size={16} />
              </ActionIcon>
            </Tooltip>
          ) : (
            <Tooltip label="Start" withArrow>
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={handleStart}
                disabled={startMutation.isPending}
              >
                <IconPlayerPlay size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          <Tooltip label="Go to project" withArrow>
            <ActionIcon
              variant="subtle"
              size="sm"
              onClick={() => void navigate(`/projects/${projectName}`)}
            >
              <IconExternalLink size={16} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Remove from scenario" withArrow>
            <ActionIcon
              variant="subtle"
              size="sm"
              onClick={onRemove}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
    </Paper>
  );
};
