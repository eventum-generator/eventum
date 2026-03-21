import { Group, Indicator, Paper, Text, Title } from '@mantine/core';
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import { IconDatabase, IconPlayerPlay, IconRoute } from '@tabler/icons-react';
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
  highlightedNodeId?: string | null;
  highlightedEdgeId?: string | null;
  onInstanceClick?: (instanceId: string) => void;
  onKeyClick?: (keyName: string) => void;
}

type InstanceNodeData = {
  label: string;
  statusColor: string;
  processing: boolean;
  highlighted: boolean;
};

type KeyNodeData = {
  label: string;
  highlighted: boolean;
};

type InstanceNodeType = Node<InstanceNodeData, 'instance'>;
type KeyNodeType = Node<KeyNodeData, 'key'>;

const InstanceNode = memo(({ data }: NodeProps<InstanceNodeType>) => (
  <Paper
    withBorder
    p="sm"
    style={{
      minWidth: 180,
      cursor: 'pointer',
      borderStyle: 'solid',
      borderColor: data.highlighted
        ? 'var(--mantine-primary-color-filled)'
        : undefined,
      boxShadow: data.highlighted
        ? '0 0 8px var(--mantine-primary-color-filled)'
        : undefined,
    }}
  >
    <Handle
      type="source"
      position={Position.Right}
      id="source"
      style={{
        background: 'var(--mantine-color-dimmed)',
        top: '35%',
      }}
      isConnectable={false}
    />
    <Handle
      type="target"
      position={Position.Right}
      id="target"
      style={{
        background: 'var(--mantine-color-dimmed)',
        top: '65%',
      }}
      isConnectable={false}
    />
    <Group gap="xs" wrap="nowrap">
      <Indicator
        color={data.statusColor}
        size={8}
        position="middle-center"
        processing={data.processing}
      />
      <IconPlayerPlay size={14} />
      <Text size="sm" fw={500}>
        {data.label}
      </Text>
    </Group>
  </Paper>
));
InstanceNode.displayName = 'InstanceNode';

const KeyNode = memo(({ data }: NodeProps<KeyNodeType>) => (
  <Paper
    withBorder
    p="sm"
    style={{
      minWidth: 140,
      cursor: 'pointer',
      borderStyle: 'dashed',
      borderColor: data.highlighted
        ? 'var(--mantine-primary-color-filled)'
        : undefined,
      boxShadow: data.highlighted
        ? '0 0 8px var(--mantine-primary-color-filled)'
        : undefined,
    }}
  >
    <Handle
      type="target"
      position={Position.Left}
      id="target"
      style={{
        background: 'var(--mantine-color-dimmed)',
        top: '35%',
      }}
      isConnectable={false}
    />
    <Handle
      type="source"
      position={Position.Left}
      id="source"
      style={{
        background: 'var(--mantine-color-dimmed)',
        top: '65%',
      }}
      isConnectable={false}
    />
    <Group gap="xs" wrap="nowrap">
      <IconDatabase size={14} />
      <Text size="sm" ff="monospace">
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
  strokeWidth: 2,
  opacity: 0.6,
};

const edgeDimmedStyle = {
  ...edgeStyle,
  opacity: 0.15,
};

const edgeHighlightedStyle = {
  ...edgeStyle,
  opacity: 1,
  strokeWidth: 3,
};

export function DataFlowDiagram({
  scenarioEntries,
  generatorStatusMap,
  globalsUsageMap,
  highlightedNodeId,
  highlightedEdgeId,
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

    // Create instance nodes on the left
    for (const [i, entry] of scenarioEntries.entries()) {
      const status =
        generatorStatusMap.get(entry.id) ?? defaultInactiveStatus;
      const { color, processing } = describeInstanceStatus(status);

      instanceNodes.push({
        id: `instance-${entry.id}`,
        type: 'instance',
        position: { x: 30, y: i * 100 + 30 },
        data: {
          label: entry.id,
          statusColor: color,
          processing,
          highlighted: highlightedNodeId === `instance-${entry.id}`,
        },
        draggable: false,
      });
    }

    // Create key nodes on the right
    for (const [i, key] of keyList.entries()) {
      instanceNodes.push({
        id: `key-${key}`,
        type: 'key',
        position: { x: 500, y: i * 100 + 30 },
        data: {
          label: key,
          highlighted: highlightedNodeId === `key-${key}`,
        },
        draggable: false,
      });
    }

    // Determine if any highlight is active
    const hasHighlight = (highlightedNodeId !== null && highlightedNodeId !== undefined) || (highlightedEdgeId !== null && highlightedEdgeId !== undefined);

    // Create edges
    for (const [generatorId, usage] of globalsUsageMap.entries()) {
      if (!usage) continue;

      for (const ref of usage.writes) {
        const sourceNodeId = `instance-${generatorId}`;
        const targetNodeId = `key-${ref.key}`;
        const edgeId = `write-${generatorId}-${ref.key}`;

        const isThisEdge = highlightedEdgeId === edgeId;
        const isConnectedToNode =
          sourceNodeId === highlightedNodeId || targetNodeId === highlightedNodeId;

        const style = hasHighlight
          ? isThisEdge || isConnectedToNode
            ? edgeHighlightedStyle
            : edgeDimmedStyle
          : edgeStyle;

        flowEdges.push({
          id: edgeId,
          source: sourceNodeId,
          target: targetNodeId,
          sourceHandle: 'source',
          targetHandle: 'target',
          type: 'default',
          animated: true,
          style,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: 'var(--mantine-color-text)',
          },
        });
      }

      // Read edges: key → instance
      for (const ref of usage.reads) {
        const sourceNodeId = `key-${ref.key}`;
        const targetNodeId = `instance-${generatorId}`;
        const edgeId = `read-${generatorId}-${ref.key}`;

        const isThisEdge = highlightedEdgeId === edgeId;
        const isConnectedToNode =
          sourceNodeId === highlightedNodeId || targetNodeId === highlightedNodeId;

        const style = hasHighlight
          ? isThisEdge || isConnectedToNode
            ? edgeHighlightedStyle
            : edgeDimmedStyle
          : edgeStyle;

        flowEdges.push({
          id: edgeId,
          source: sourceNodeId,
          target: targetNodeId,
          sourceHandle: 'source',
          targetHandle: 'target',
          type: 'default',
          animated: true,
          style,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: 'var(--mantine-color-text)',
          },
        });
      }
    }

    const maxNodeCount = Math.max(instanceCount, keyCount);
    const height = Math.max(220, maxNodeCount * 100 + 60);

    return { nodes: instanceNodes, edges: flowEdges, containerHeight: height };
  }, [scenarioEntries, generatorStatusMap, globalsUsageMap, highlightedNodeId, highlightedEdgeId]);

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
      <Group gap="xs" mb="sm">
        <IconRoute size={18} />
        <Title order={5} fw="normal">
          Data Flow
        </Title>
      </Group>
      <style>{`
        .react-flow__controls button {
          background-color: var(--mantine-color-body);
          color: var(--mantine-color-text);
          border-color: var(--mantine-color-default-border);
        }
        .react-flow__controls button:hover {
          background-color: var(--mantine-color-default-hover);
        }
        .react-flow__controls button svg {
          fill: var(--mantine-color-text);
        }
      `}</style>
      <div style={{ height: containerHeight }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.5 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </Paper>
  );
}
