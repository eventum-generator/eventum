import { Group, Indicator, Paper, Text, Title } from '@mantine/core';
import {
  Background,
  BackgroundVariant,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import { IconDatabase, IconPlayerPlay } from '@tabler/icons-react';
import { memo, useMemo } from 'react';

import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

import '@xyflow/react/dist/style.css';

interface DataFlowDiagramProps {
  scenarioEntries: { id: string; path: string }[];
  generatorStatusMap: Map<string, GeneratorStatus>;
  globalsUsageMap: Map<
    string,
    { writes: { key: string }[]; reads: { key: string }[] } | undefined
  >;
  onInstanceClick?: (instanceId: string) => void;
  onKeyClick?: (keyName: string) => void;
}

type InstanceNodeData = {
  label: string;
  statusColor: string;
  processing: boolean;
};

type KeyNodeData = {
  label: string;
};

type InstanceNodeType = Node<InstanceNodeData, 'instance'>;
type KeyNodeType = Node<KeyNodeData, 'key'>;

const InstanceNode = memo(({ data }: NodeProps<InstanceNodeType>) => (
  <Paper
    withBorder
    p="xs"
    style={{ minWidth: 140, cursor: 'pointer', borderStyle: 'solid' }}
  >
    <Handle
      type="source"
      position={Position.Right}
      style={{ background: 'var(--mantine-color-dimmed)' }}
    />
    <Handle
      type="target"
      position={Position.Right}
      style={{ background: 'var(--mantine-color-dimmed)' }}
    />
    <Group gap="xs" wrap="nowrap">
      <Indicator
        color={data.statusColor}
        size={8}
        position="middle-center"
        processing={data.processing}
      />
      <IconPlayerPlay size={12} />
      <Text size="xs" fw={500}>
        {data.label}
      </Text>
    </Group>
  </Paper>
));
InstanceNode.displayName = 'InstanceNode';

const KeyNode = memo(({ data }: NodeProps<KeyNodeType>) => (
  <Paper
    withBorder
    p="xs"
    style={{ minWidth: 100, cursor: 'pointer', borderStyle: 'dashed' }}
  >
    <Handle
      type="target"
      position={Position.Left}
      style={{ background: 'var(--mantine-color-dimmed)' }}
    />
    <Handle
      type="source"
      position={Position.Left}
      style={{ background: 'var(--mantine-color-dimmed)' }}
    />
    <Group gap="xs" wrap="nowrap">
      <IconDatabase size={12} />
      <Text size="xs" ff="monospace">
        {data.label}
      </Text>
    </Group>
  </Paper>
));
KeyNode.displayName = 'KeyNode';

const defaultInactiveStatus: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const edgeStyle = {
  strokeDasharray: '5,5',
  stroke: 'var(--mantine-color-text)',
  strokeWidth: 1.5,
  opacity: 0.4,
};

export function DataFlowDiagram({
  scenarioEntries,
  generatorStatusMap,
  globalsUsageMap,
  onInstanceClick,
  onKeyClick,
}: DataFlowDiagramProps) {
  const nodeTypes = useMemo(
    () => ({ instance: InstanceNode, key: KeyNode }),
    []
  );

  const { nodes, edges, containerHeight } = useMemo(() => {
    const instanceNodes: (InstanceNodeType | KeyNodeType)[] = [];
    const flowEdges: Edge[] = [];
    const edgeIds = new Set<string>();

    // Collect all unique global keys
    const allKeys = new Set<string>();
    for (const usage of globalsUsageMap.values()) {
      if (!usage) continue;
      for (const ref of usage.writes) allKeys.add(ref.key);
      for (const ref of usage.reads) allKeys.add(ref.key);
    }

    const keyList = [...allKeys].sort();
    const instanceCount = scenarioEntries.length;
    const keyCount = keyList.length;

    // Vertical spacing
    const instanceSpacing =
      instanceCount > 1 ? 200 / (instanceCount - 1) : 0;
    const keySpacing = keyCount > 1 ? 200 / (keyCount - 1) : 0;
    const instanceStartY =
      instanceCount > 1 ? 25 : 100;
    const keyStartY = keyCount > 1 ? 25 : 100;

    // Create instance nodes on the left
    for (const [i, entry] of scenarioEntries.entries()) {
      const status =
        generatorStatusMap.get(entry.id) ?? defaultInactiveStatus;
      const { color, processing } = describeInstanceStatus(status);

      instanceNodes.push({
        id: `instance-${entry.id}`,
        type: 'instance',
        position: { x: 50, y: instanceStartY + i * instanceSpacing },
        data: {
          label: entry.id,
          statusColor: color,
          processing,
        },
        draggable: false,
      });
    }

    // Create key nodes on the right
    for (const [i, key] of keyList.entries()) {
      instanceNodes.push({
        id: `key-${key}`,
        type: 'key',
        position: { x: 450, y: keyStartY + i * keySpacing },
        data: { label: key },
        draggable: false,
      });
    }

    // Create edges — all animated dashed, no labels
    for (const [generatorId, usage] of globalsUsageMap.entries()) {
      if (!usage) continue;

      // Write edges: instance → key
      for (const ref of usage.writes) {
        const edgeId = `write-${generatorId}-${ref.key}`;
        if (edgeIds.has(edgeId)) continue;
        edgeIds.add(edgeId);

        flowEdges.push({
          id: edgeId,
          source: `instance-${generatorId}`,
          target: `key-${ref.key}`,
          sourceHandle: null,
          targetHandle: null,
          type: 'default',
          animated: true,
          style: edgeStyle,
        });
      }

      // Read edges: key → instance
      for (const ref of usage.reads) {
        const edgeId = `read-${generatorId}-${ref.key}`;
        if (edgeIds.has(edgeId)) continue;
        edgeIds.add(edgeId);

        flowEdges.push({
          id: edgeId,
          source: `key-${ref.key}`,
          target: `instance-${generatorId}`,
          sourceHandle: null,
          targetHandle: null,
          type: 'default',
          animated: true,
          style: edgeStyle,
        });
      }
    }

    const nodeCount = Math.max(instanceCount, keyCount);
    const height = Math.max(180, nodeCount * 80 + 40);

    return { nodes: instanceNodes, edges: flowEdges, containerHeight: height };
  }, [scenarioEntries, generatorStatusMap, globalsUsageMap]);

  function handleNodeClick(_: React.MouseEvent, node: InstanceNodeType | KeyNodeType) {
    if (node.type === 'instance') {
      const instanceId = node.id.replace('instance-', '');
      onInstanceClick?.(instanceId);
    } else if (node.type === 'key') {
      const keyName = node.id.replace('key-', '');
      onKeyClick?.(keyName);
    }
  }

  return (
    <Paper withBorder p="md">
      <Title order={5} fw="normal" mb="sm">
        Data Flow
      </Title>
      <div style={{ height: containerHeight }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.5 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        </ReactFlow>
      </div>
    </Paper>
  );
}
