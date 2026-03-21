import {
  ActionIcon,
  Box,
  Code,
  Collapse,
  Group,
  Indicator,
  Paper,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconChevronDown,
  IconChevronRight,
  IconExternalLink,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { dirname } from 'pathe';
import { FC, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  useStartGeneratorMutation,
  useStopGeneratorMutation,
} from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { GlobalsUsage } from '@/api/routes/scenarios/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

export interface GeneratorCardProps {
  generatorId: string;
  generatorPath: string;
  status?: GeneratorStatus;
  globalsUsage?: GlobalsUsage;
  onRemove: () => void;
  onHover?: (nodeId: string | null) => void;
  onHighlightEdge?: (generatorId: string, keyName: string) => void;
}

export const GeneratorCard: FC<GeneratorCardProps> = ({
  generatorId,
  generatorPath,
  status,
  globalsUsage,
  onRemove,
  onHover,
  onHighlightEdge,
}) => {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);

  const startMutation = useStartGeneratorMutation();
  const stopMutation = useStopGeneratorMutation();

  const projectName = dirname(generatorPath);
  const isActive = status?.is_running ?? false;
  const isTransitioning =
    (status?.is_initializing ?? false) || (status?.is_stopping ?? false);
  const statusInfo = status
    ? describeInstanceStatus(status)
    : { text: 'Inactive', color: 'gray.6' as const, processing: false };

  const hasGlobalsDetails =
    (globalsUsage?.writes.length ?? 0) > 0 ||
    (globalsUsage?.reads.length ?? 0) > 0;

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
    <Paper
      withBorder
      p="sm"
      onMouseEnter={() => onHover?.(`instance-${generatorId}`)}
      onMouseLeave={() => onHover?.(null)}
    >
      <Group justify="space-between" align="center" wrap="nowrap">
        <Group gap="sm" align="center" wrap="nowrap" style={{ minWidth: 0 }}>
          {hasGlobalsDetails ? (
            <UnstyledButton
              onClick={() => setExpanded((prev) => !prev)}
              style={{ lineHeight: 0 }}
            >
              {expanded ? (
                <IconChevronDown size={14} />
              ) : (
                <IconChevronRight size={14} />
              )}
            </UnstyledButton>
          ) : (
            <Box w={14} />
          )}
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
                onClick={handleStop}
                disabled={stopMutation.isPending}
              >
                <IconPlayerStop size={18} />
              </ActionIcon>
            </Tooltip>
          ) : (
            <Tooltip label="Start" withArrow>
              <ActionIcon
                variant="subtle"
                onClick={handleStart}
                disabled={startMutation.isPending}
              >
                <IconPlayerPlay size={18} />
              </ActionIcon>
            </Tooltip>
          )}
          <Tooltip label="Go to project" withArrow>
            <ActionIcon
              variant="subtle"
              onClick={() => void navigate(`/projects/${projectName}`)}
            >
              <IconExternalLink size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Remove from scenario" withArrow>
            <ActionIcon
              variant="subtle"
              onClick={onRemove}
            >
              <IconTrash size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      <Collapse in={expanded}>
        <Stack gap="xs" mt="xs" pl="md">
          {globalsUsage?.writes.map((w, i) => (
            <Stack
              key={`w-${i}`}
              gap={2}
              onMouseEnter={() => onHighlightEdge?.(generatorId, w.key)}
              onMouseLeave={() => onHighlightEdge?.('', '')}
            >
              <Text size="xs" c="dimmed">
                Writes{' '}
                <Text span ff="monospace" fw={500}>
                  {w.key}
                </Text>{' '}
                in {w.template}:{w.line}
              </Text>
              <Code block style={{ fontSize: 11 }}>
                {w.snippet}
              </Code>
            </Stack>
          ))}
          {globalsUsage?.reads.map((r, i) => (
            <Stack
              key={`r-${i}`}
              gap={2}
              onMouseEnter={() => onHighlightEdge?.(generatorId, r.key)}
              onMouseLeave={() => onHighlightEdge?.('', '')}
            >
              <Text size="xs" c="dimmed">
                Reads{' '}
                <Text span ff="monospace" fw={500}>
                  {r.key}
                </Text>{' '}
                in {r.template}:{r.line}
              </Text>
              <Code block style={{ fontSize: 11 }}>
                {r.snippet}
              </Code>
            </Stack>
          ))}
        </Stack>
      </Collapse>
    </Paper>
  );
};
