import {
  ActionIcon,
  Box,
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
  IconEye,
  IconFile,
  IconPlayerPlay,
  IconPlayerStop,
  IconTrash,
} from '@tabler/icons-react';
import { dirname } from 'pathe';
import { FC, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { TemplatePreviewModal } from './TemplatePreviewModal';
import {
  useStartGeneratorMutation,
  useStopGeneratorMutation,
} from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { GlobalsUsage } from '@/api/routes/scenarios/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';
import { ROUTE_PATHS } from '@/routing/paths';

export interface GeneratorCardProps {
  generatorId: string;
  generatorPath: string;
  status?: GeneratorStatus;
  globalsUsage?: GlobalsUsage;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onRemove: () => void;
  onHover?: (nodeId: string | null) => void;
  onHighlightEdge?: (generatorId: string, keyName: string) => void;
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
  const navigate = useNavigate();
  const [internalExpanded, setInternalExpanded] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<string | null>(null);

  // Use external expand state if provided, otherwise fall back to internal
  const expanded = externalExpanded ?? internalExpanded;
  const toggleExpand = onToggleExpand ?? (() => setInternalExpanded((prev) => !prev));

  const startMutation = useStartGeneratorMutation();
  const stopMutation = useStopGeneratorMutation();

  const projectName = dirname(generatorPath);
  const isActive = status?.is_running ?? false;
  const isTransitioning =
    (status?.is_initializing ?? false) || (status?.is_stopping ?? false);
  const hasStatus = status !== undefined;
  const statusInfo = status
    ? describeInstanceStatus(status)
    : { text: 'Inactive', color: 'gray.6' as const, processing: false };

  const hasGlobalsDetails =
    (globalsUsage?.writes.length ?? 0) > 0 ||
    (globalsUsage?.reads.length ?? 0) > 0;

  // Group globals usage by template name
  const templateMap = useMemo(() => {
    const map = new Map<string, { writes: string[]; reads: string[] }>();
    for (const w of globalsUsage?.writes ?? []) {
      if (!map.has(w.template)) map.set(w.template, { writes: [], reads: [] });
      const entry = map.get(w.template)!;
      if (!entry.writes.includes(w.key)) entry.writes.push(w.key);
    }
    for (const r of globalsUsage?.reads ?? []) {
      if (!map.has(r.template)) map.set(r.template, { writes: [], reads: [] });
      const entry = map.get(r.template)!;
      if (!entry.reads.includes(r.key)) entry.reads.push(r.key);
    }
    return map;
  }, [globalsUsage]);

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
        {/* Issue 8: Entire left area is clickable to toggle expand */}
        <UnstyledButton
          onClick={toggleExpand}
          style={{ minWidth: 0, cursor: 'pointer' }}
        >
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
        </UnstyledButton>

        {/* Issue 5: size="md" and icon size 20 */}
        <Group gap={4} wrap="nowrap">
          {isActive || isTransitioning ? (
            <Tooltip label="Stop" withArrow>
              <ActionIcon
                variant="subtle"
                size="md"
                onClick={handleStop}
                disabled={stopMutation.isPending}
              >
                <IconPlayerStop size={20} />
              </ActionIcon>
            </Tooltip>
          ) : (
            <Tooltip label="Start" withArrow>
              <ActionIcon
                variant="subtle"
                size="md"
                onClick={handleStart}
                disabled={startMutation.isPending}
              >
                <IconPlayerPlay size={20} />
              </ActionIcon>
            </Tooltip>
          )}
          {/* Issue 7: View instance action */}
          {hasStatus && (
            <Tooltip label="View instance" withArrow>
              <ActionIcon
                variant="subtle"
                size="md"
                onClick={() =>
                  void navigate(`${ROUTE_PATHS.INSTANCES}/${generatorId}`)
                }
              >
                <IconEye size={20} />
              </ActionIcon>
            </Tooltip>
          )}
          <Tooltip label="Go to project" withArrow>
            <ActionIcon
              variant="subtle"
              size="md"
              onClick={() => void navigate(`/projects/${projectName}`)}
            >
              <IconExternalLink size={20} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Remove from scenario" withArrow>
            <ActionIcon
              variant="subtle"
              size="md"
              onClick={onRemove}
            >
              <IconTrash size={20} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {/* Issue 4: Show template names grouped by file, not code snippets */}
      <Collapse in={expanded}>
        <Stack gap="xs" mt="xs" pl="md">
          {hasGlobalsDetails && (
            <Text size="xs" fw={500} c="dimmed">
              Templates:
            </Text>
          )}
          {[...templateMap.entries()].map(([template, usage]) => (
            <Stack key={template} gap={2}>
              <UnstyledButton
                onClick={() => setPreviewTemplate(template)}
                onMouseEnter={() => {
                  const firstKey = usage.writes[0] ?? usage.reads[0];
                  if (firstKey) onHighlightEdge?.(generatorId, firstKey);
                }}
                onMouseLeave={() => onHighlightEdge?.('', '')}
                style={{ cursor: 'pointer' }}
              >
                <Group gap="xs" wrap="nowrap">
                  <IconFile size={14} style={{ flexShrink: 0 }} />
                  <Text size="xs" ff="monospace" fw={500} td="underline">
                    {template}
                  </Text>
                </Group>
              </UnstyledButton>
              {usage.writes.map((key) => (
                <Text key={`w-${key}`} size="xs" c="dimmed" pl={22}>
                  &rarr;{' '}
                  <Text span ff="monospace" size="xs">{key}</Text>
                  {' '}
                  <Text span size="xs" c="dimmed">(write)</Text>
                </Text>
              ))}
              {usage.reads.map((key) => (
                <Text key={`r-${key}`} size="xs" c="dimmed" pl={22}>
                  &larr;{' '}
                  <Text span ff="monospace" size="xs">{key}</Text>
                  {' '}
                  <Text span size="xs" c="dimmed">(read)</Text>
                </Text>
              ))}
            </Stack>
          ))}
        </Stack>
      </Collapse>

      <TemplatePreviewModal
        opened={previewTemplate !== null}
        onClose={() => setPreviewTemplate(null)}
        generatorName={generatorId}
        templatePath={previewTemplate ?? ''}
      />
    </Paper>
  );
};
