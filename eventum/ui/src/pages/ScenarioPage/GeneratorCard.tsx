import {
  ActionIcon,
  Box,
  Collapse,
  Group,
  Indicator,
  Menu,
  Paper,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconChevronDown,
  IconChevronRight,
  IconArrowRight,
  IconArrowLeft,
  IconDotsVertical,
  IconExternalLink,
  IconFile,
  IconGauge,
  IconLogs,
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
import { streamGeneratorLogs } from '@/api/routes/generators';
import { LogsModal } from '@/components/modals/LogsModal';
import { MetricsModal } from '@/pages/InstancesPage/InstancesTable/MetricsModal';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { GlobalsUsage } from '@/api/routes/scenarios/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

export interface GeneratorCardProps {
  generatorId: string;
  generatorPath: string;
  status?: GeneratorStatus;
  globalsUsage?: GlobalsUsage;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onRemove: () => void;
  onHover?: (nodeId: string | null) => void;
  onHighlightEdge?: (generatorId: string, keyName: string, direction?: 'write' | 'read') => void;
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

  const GLOBALS_ROW_STYLE = { cursor: 'default', borderRadius: 4, padding: '2px 4px 2px 22px' } as const;

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
          showSuccessNotification('Success', `Instance "${generatorId}" started`),
        onError: (error) =>
          showErrorNotification('Failed to start instance', error),
      }
    );
  }

  function handleStop() {
    stopMutation.mutate(
      { id: generatorId },
      {
        onSuccess: () =>
          showSuccessNotification('Success', `Instance "${generatorId}" stopped`),
        onError: (error) =>
          showErrorNotification('Failed to stop instance', error),
      }
    );
  }

  function handleShowMetrics() {
    modals.open({
      title: 'Instance metrics',
      children: <MetricsModal instanceId={generatorId} />,
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
        <Group justify="space-between" align="center" wrap="nowrap">
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
          </Group>

          <Menu shadow="md" width={170} position="bottom-end">
            <Menu.Target>
              <ActionIcon
                variant="subtle"
                size="sm"
                aria-label="Instance actions"
                onClick={(e) => e.stopPropagation()}
              >
                <IconDotsVertical size={16} />
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
              leftSection={<IconExternalLink size={14} />}
              onClick={() => void navigate(`${ROUTE_PATHS.INSTANCES}/${generatorId}`)}
            >
              Edit instance
            </Menu.Item>
            <Menu.Item
              leftSection={<IconExternalLink size={14} />}
              onClick={() => void navigate(`${ROUTE_PATHS.PROJECTS}/${projectName}`)}
            >
              Go to project
            </Menu.Item>
            <Menu.Divider />
            <Menu.Item
              color="red"
              leftSection={<IconTrash size={14} />}
              onClick={onRemove}
            >
              Remove
            </Menu.Item>
          </Menu.Dropdown>
          </Menu>
        </Group>
      </UnstyledButton>

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
                <Group
                  key={`w-${key}`}
                  gap={4}
                  pl={22}
                  wrap="nowrap"
                  style={GLOBALS_ROW_STYLE}
                  onMouseEnter={() => onHighlightEdge?.(generatorId, key, 'write')}
                  onMouseLeave={() => onHighlightEdge?.('', '')}
                >
                  <IconArrowRight size={12} style={{ flexShrink: 0 }} />
                  <Text size="xs" ff="monospace">{key}</Text>
                  <Text size="xs" c="dimmed">(write)</Text>
                </Group>
              ))}
              {usage.reads.map((key) => (
                <Group
                  key={`r-${key}`}
                  gap={4}
                  pl={22}
                  wrap="nowrap"
                  style={GLOBALS_ROW_STYLE}
                  onMouseEnter={() => onHighlightEdge?.(generatorId, key, 'read')}
                  onMouseLeave={() => onHighlightEdge?.('', '')}
                >
                  <IconArrowLeft size={12} style={{ flexShrink: 0 }} />
                  <Text size="xs" ff="monospace">{key}</Text>
                  <Text size="xs" c="dimmed">(read)</Text>
                </Group>
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
