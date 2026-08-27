import {
  ActionIcon,
  Box,
  Collapse,
  Group,
  Menu,
  Paper,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconChevronDown,
  IconChevronRight,
  IconDotsVertical,
  IconExternalLink,
  IconGauge,
  IconLogs,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { FC, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { SourceUsage } from './SourceUsage';
import { buildSourceUsage } from './source-usage';
import {
  useStartGeneratorMutation,
  useStopGeneratorMutation,
  useUpdateGeneratorStatus,
} from '@/api/hooks/useGenerators';
import { streamGeneratorLogs } from '@/api/routes/generators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { GlobalsUsage } from '@/api/routes/scenarios/schemas';
import { LogsModal } from '@/components/modals/LogsModal';
import { StatusPill } from '@/components/ui/StatusPill';
import { InstanceMetrics } from '@/pages/InstancesPage/InstancesTable/metrics/InstanceMetrics';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';
import { projectOfConfig } from '@/utils/projectPath';

// Fallback for a member whose live status is not loaded yet, so the status
// pill always renders (reads as inactive until the real status arrives).
const INACTIVE_STATUS: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_stopping: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
};

export interface GeneratorCardProps {
  generatorId: string;
  generatorPath: string;
  status?: GeneratorStatus;
  globalsUsage?: GlobalsUsage;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onRemove: () => void;
  onHover?: (nodeId: string | null) => void;
  onHighlightEdge?: (
    generatorId: string,
    keyName: string,
    direction?: 'write' | 'read'
  ) => void;
}

export const GeneratorCard: FC<GeneratorCardProps> = ({
  generatorId,
  generatorPath,
  status,
  globalsUsage,
  isExpanded: externalExpanded,
  onToggleExpand,
  onRemove,
  onHover,
  onHighlightEdge,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(false);

  // Use external expand state if provided, otherwise fall back to internal
  const expanded = externalExpanded ?? internalExpanded;
  const toggleExpand =
    onToggleExpand ?? (() => setInternalExpanded((prev) => !prev));

  const startMutation = useStartGeneratorMutation();
  const stopMutation = useStopGeneratorMutation();
  const updateStatus = useUpdateGeneratorStatus();

  const project = projectOfConfig(generatorPath);
  const isActive = status?.is_running ?? false;
  const isTransitioning =
    (status?.is_initializing ?? false) || (status?.is_stopping ?? false);

  const templateEntries = useMemo(
    () => buildSourceUsage(globalsUsage),
    [globalsUsage]
  );
  const hasGlobalsDetails = templateEntries.length > 0;

  function handleStart() {
    updateStatus.mutate({
      id: generatorId,
      status: {
        is_initializing: true,
        is_running: false,
        is_stopping: false,
        is_ended_up: false,
        is_ended_up_successfully: false,
      },
    });
    startMutation.mutate(
      { id: generatorId },
      {
        onSuccess: () =>
          showSuccessNotification(
            'Success',
            `Instance "${generatorId}" started`
          ),
        onError: (error) =>
          showErrorNotification('Failed to start instance', error),
      }
    );
  }

  function handleStop() {
    updateStatus.mutate({
      id: generatorId,
      status: {
        is_initializing: false,
        is_running: false,
        is_stopping: true,
        is_ended_up: false,
        is_ended_up_successfully: false,
      },
    });
    stopMutation.mutate(
      { id: generatorId },
      {
        onSuccess: () =>
          showSuccessNotification(
            'Success',
            `Instance "${generatorId}" stopped`
          ),
        onError: (error) =>
          showErrorNotification('Failed to stop instance', error),
      }
    );
  }

  function handleShowMetrics() {
    modals.open({
      title: 'Instance metrics',
      children: <InstanceMetrics instanceId={generatorId} />,
      size: 'xl',
    });
  }

  function handleShowLogs() {
    modals.open({
      title: 'Instance logs',
      children: (
        <LogsModal
          getWebSocket={() => streamGeneratorLogs(generatorId, 10_048_576)}
        />
      ),
      size: '80vw',
    });
  }

  return (
    <Paper
      withBorder
      p="sm"
      onMouseEnter={() => onHover?.(`instance-${generatorId}`)}
      onMouseLeave={() => onHover?.(null)}
    >
      <UnstyledButton
        onClick={toggleExpand}
        style={{ width: '100%', cursor: 'pointer' }}
      >
        <Group justify="space-between" align="center" wrap="nowrap" gap="sm">
          <Group gap="sm" align="center" wrap="nowrap" style={{ minWidth: 0 }}>
            {hasGlobalsDetails ? (
              <Box style={{ lineHeight: 0 }}>
                {expanded ? (
                  <IconChevronDown size={14} />
                ) : (
                  <IconChevronRight size={14} />
                )}
              </Box>
            ) : (
              <Box w={14} />
            )}
            <Stack gap={0} style={{ minWidth: 0 }}>
              <Text size="sm" fw={500} truncate>
                {generatorId}
              </Text>
              <Text size="xs" c="dimmed" truncate title={generatorPath}>
                {project.inWorkspace ? project.name : generatorPath}
              </Text>
            </Stack>
          </Group>

          <Group
            gap="xs"
            align="center"
            wrap="nowrap"
            style={{ flexShrink: 0 }}
          >
            <StatusPill status={status ?? INACTIVE_STATUS} />
            <Menu shadow="md" width={170} position="bottom-end">
              <Menu.Target>
                <ActionIcon
                  variant="transparent"
                  aria-label="Instance actions"
                  onClick={(e) => e.stopPropagation()}
                >
                  <IconDotsVertical size={20} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                {isActive || isTransitioning ? (
                  <Menu.Item
                    leftSection={<IconPlayerStop size={14} />}
                    onClick={handleStop}
                    disabled={stopMutation.isPending}
                  >
                    Stop
                  </Menu.Item>
                ) : (
                  <Menu.Item
                    leftSection={<IconPlayerPlay size={14} />}
                    onClick={handleStart}
                    disabled={startMutation.isPending}
                  >
                    Start
                  </Menu.Item>
                )}
                <Menu.Divider />
                <Menu.Item
                  leftSection={<IconGauge size={14} />}
                  onClick={handleShowMetrics}
                  disabled={!isActive}
                >
                  Show metrics
                </Menu.Item>
                <Menu.Item
                  leftSection={<IconLogs size={14} />}
                  onClick={handleShowLogs}
                >
                  Show logs
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item
                  component={Link}
                  to={`${ROUTE_PATHS.INSTANCES}/${generatorId}`}
                  leftSection={<IconExternalLink size={14} />}
                >
                  Edit instance
                </Menu.Item>
                {/* A configuration registered from outside the
                    workspace has no project page to open. */}
                {project.inWorkspace && (
                  <Menu.Item
                    component={Link}
                    to={`${ROUTE_PATHS.PROJECTS}/${project.name}`}
                    leftSection={<IconExternalLink size={14} />}
                  >
                    Go to project
                  </Menu.Item>
                )}
                <Menu.Divider />
                <Menu.Item
                  color="var(--mantine-color-red-text)"
                  leftSection={<IconTrash size={14} />}
                  onClick={onRemove}
                >
                  Remove
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </UnstyledButton>

      <Collapse in={expanded}>
        <SourceUsage
          generatorId={generatorId}
          entries={templateEntries}
          onHighlightEdge={onHighlightEdge}
          onHoverNode={onHover}
        />
      </Collapse>
    </Paper>
  );
};
