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
  <Paper withBorder p="xs" style={{ minWidth: 140 }}>
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
      <Text size="xs" fw={500}>
        {data.label}
      </Text>
    </Group>
  </Paper>
));
InstanceNode.displayName = 'InstanceNode';

const KeyNode = memo(({ data }: NodeProps<KeyNodeType>) => (
  <Paper withBorder p="xs" style={{ minWidth: 100 }}>
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
    <Text size="xs" ff="monospace">
      {data.label}
    </Text>
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

export function DataFlowDiagram({
  scenarioEntries,
  generatorStatusMap,
  globalsUsageMap,
}: DataFlowDiagramProps) {
  const nodeTypes = useMemo(
    () => ({ instance: InstanceNode, key: KeyNode }),
    []
  );

  const { nodes, edges } = useMemo(() => {
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

    // Create edges
    for (const [generatorId, usage] of globalsUsageMap.entries()) {
      if (!usage) continue;

      // Write edges: instance → key (solid)
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
          label: 'writes',
          animated: false,
          style: {
            stroke: 'var(--mantine-color-dimmed)',
          },
          labelStyle: {
            fontSize: 10,
            fill: 'var(--mantine-color-text)',
          },
        });
      }

      // Read edges: key → instance (dashed)
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
          label: 'reads',
          animated: true,
          style: {
            stroke: 'var(--mantine-color-dimmed)',
            strokeDasharray: '5,5',
          },
          labelStyle: {
            fontSize: 10,
            fill: 'var(--mantine-color-text)',
          },
        });
      }
    }

    return { nodes: instanceNodes, edges: flowEdges };
  }, [scenarioEntries, generatorStatusMap, globalsUsageMap]);

  return (
    <Paper withBorder p="md">
      <Title order={5} fw="normal" mb="sm">
        Data Flow
      </Title>
      <div style={{ height: 250 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        </ReactFlow>
      </div>
    </Paper>
  );
}
