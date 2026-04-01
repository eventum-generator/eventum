import { Group, Indicator, Paper, Text, Title } from '@mantine/core';
import { IconDatabase, IconPlayerPlay, IconRoute } from '@tabler/icons-react';
import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  Handle,
  MarkerType,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { memo, useMemo } from 'react';

import { collectGlobalKeys } from './globals-usage';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DataFlowDiagramProps {
  readonly scenarioEntries: { id: string; path: string }[];
  readonly generatorStatusMap: Map<string, GeneratorStatus>;
  readonly globalsUsageMap: Map<
    string,
    { writes: { key: string }[]; reads: { key: string }[] } | undefined
  >;
  readonly highlightedNodeId?: string | null;
  readonly highlightedEdgeId?: string | null;
  readonly onInstanceClick?: (instanceId: string) => void;
}

// React Flow's Node<T> requires T extends Record<string, unknown>,
// which interfaces don't satisfy — use type aliases here.
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type InstanceNodeData = {
  label: string;
  statusColor: string;
  processing: boolean;
  highlighted: boolean;
};

// eslint-disable-next-line @typescript-eslint/consistent-type-definitions
type KeyNodeData = {
  label: string;
  highlighted: boolean;
};

type InstanceNodeType = Node<InstanceNodeData, 'instance'>;
type KeyNodeType = Node<KeyNodeData, 'key'>;
type DiagramNode = InstanceNodeType | KeyNodeType;

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------

const INSTANCE_X = 30;
const KEY_X = 500;
const NODE_SPACING_Y = 100;
const PADDING_TOP = 30;
const MIN_DIAGRAM_HEIGHT = 220;
const DIAGRAM_BOTTOM_PADDING = 60;

// ---------------------------------------------------------------------------
// Edge styles
// ---------------------------------------------------------------------------

const BASE_EDGE_STYLE = {
  strokeDasharray: '5,5',
  stroke: 'var(--mantine-color-text)',
  strokeWidth: 2,
  opacity: 0.6,
} as const;

const DIMMED_EDGE_STYLE = {
  ...BASE_EDGE_STYLE,
  opacity: 0.15,
} as const;

const HIGHLIGHTED_EDGE_STYLE = {
  ...BASE_EDGE_STYLE,
  opacity: 1,
  strokeWidth: 3,
  stroke: 'var(--mantine-primary-color-filled)',
} as const;

const PRIMARY_COLOR = 'var(--mantine-primary-color-filled)';
const TEXT_COLOR = 'var(--mantine-color-text)';

// ---------------------------------------------------------------------------
// Handle styles (shared between node types, positions differ)
// ---------------------------------------------------------------------------

const HIDDEN_HANDLE_STYLE = {
  background: 'transparent',
  border: 'none',
  width: 6,
  height: 6,
} as const;

const SOURCE_HANDLE_STYLE = { ...HIDDEN_HANDLE_STYLE, top: '25%' } as const;
const TARGET_HANDLE_STYLE = { ...HIDDEN_HANDLE_STYLE, top: '75%' } as const;

// ---------------------------------------------------------------------------
// CSS for React Flow controls (Mantine theme integration)
// ---------------------------------------------------------------------------

const REACT_FLOW_CONTROLS_CSS = `
  .react-flow__controls button {
    background-color: var(--mantine-color-body);
    color: ${TEXT_COLOR};
    border-color: var(--mantine-color-default-border);
  }
  .react-flow__controls button:hover {
    background-color: var(--mantine-color-default-hover);
  }
  .react-flow__controls button svg {
    fill: ${TEXT_COLOR};
  }
`;

// ---------------------------------------------------------------------------
// Highlight style for nodes
// ---------------------------------------------------------------------------

function highlightBorderStyle(isHighlighted: boolean) {
  if (!isHighlighted) return {};
  return {
    borderColor: PRIMARY_COLOR,
    boxShadow: `0 0 8px ${PRIMARY_COLOR}`,
  };
}

// ---------------------------------------------------------------------------
// Custom nodes
// ---------------------------------------------------------------------------

const InstanceNode = memo(({ data }: NodeProps<InstanceNodeType>) => (
  <Paper
    withBorder
    p="sm"
    style={{
      minWidth: 180,
      cursor: 'pointer',
      borderStyle: 'solid',
      ...highlightBorderStyle(data.highlighted),
    }}
  >
    <Handle type="source" position={Position.Right} id="source" style={SOURCE_HANDLE_STYLE} isConnectable={false} />
    <Handle type="target" position={Position.Right} id="target" style={TARGET_HANDLE_STYLE} isConnectable={false} />
    <Group gap={8} wrap="nowrap" pr={6} justify="space-between">
      <Group gap={8} wrap="nowrap">
        <IconPlayerPlay size={14} />
        <Text size="sm" fw={500}>{data.label}</Text>
      </Group>
      <Indicator color={data.statusColor} size={8} position="middle-center" processing={data.processing} />
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
      ...highlightBorderStyle(data.highlighted),
    }}
  >
    <Handle type="target" position={Position.Left} id="target" style={SOURCE_HANDLE_STYLE} isConnectable={false} />
    <Handle type="source" position={Position.Left} id="source" style={TARGET_HANDLE_STYLE} isConnectable={false} />
    <Group gap="xs" wrap="nowrap">
      <IconDatabase size={14} />
      <Text size="sm" ff="monospace">{data.label}</Text>
    </Group>
  </Paper>
));
KeyNode.displayName = 'KeyNode';

// ---------------------------------------------------------------------------
// Default status for inactive generators
// ---------------------------------------------------------------------------

const INACTIVE_STATUS: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

// ---------------------------------------------------------------------------
// Graph building helpers (extracted to reduce cognitive complexity)
// ---------------------------------------------------------------------------

function buildInstanceNodes(
  entries: DataFlowDiagramProps['scenarioEntries'],
  statusMap: DataFlowDiagramProps['generatorStatusMap'],
  highlightedNodeId: string | null | undefined,
): DiagramNode[] {
  return entries.map((entry, i) => {
    const status = statusMap.get(entry.id) ?? INACTIVE_STATUS;
    const { color, processing } = describeInstanceStatus(status);
    const nodeId = `instance-${entry.id}`;

    return {
      id: nodeId,
      type: 'instance' as const,
      position: { x: INSTANCE_X, y: i * NODE_SPACING_Y + PADDING_TOP },
      data: {
        label: entry.id,
        statusColor: color,
        processing,
        highlighted: highlightedNodeId === nodeId,
      },
      draggable: false,
    };
  });
}

function buildKeyNodes(
  keys: string[],
  highlightedNodeId: string | null | undefined,
): DiagramNode[] {
  return keys.map((key, i) => {
    const nodeId = `key-${key}`;
    return {
      id: nodeId,
      type: 'key' as const,
      position: { x: KEY_X, y: i * NODE_SPACING_Y + PADDING_TOP },
      data: {
        label: key,
        highlighted: highlightedNodeId === nodeId,
      },
      draggable: false,
    };
  });
}

interface EdgeContext {
  highlightedNodeId: string | null | undefined;
  highlightedEdgeId: string | null | undefined;
  hasHighlight: boolean;
}

function resolveEdgeStyle(
  edgeId: string,
  sourceNodeId: string,
  targetNodeId: string,
  ctx: EdgeContext,
) {
  const isHighlighted =
    ctx.highlightedEdgeId === edgeId ||
    sourceNodeId === ctx.highlightedNodeId ||
    targetNodeId === ctx.highlightedNodeId;

  const style = ctx.hasHighlight
    ? isHighlighted ? HIGHLIGHTED_EDGE_STYLE : DIMMED_EDGE_STYLE
    : BASE_EDGE_STYLE;

  const markerColor = ctx.hasHighlight && isHighlighted ? PRIMARY_COLOR : TEXT_COLOR;

  return { style, markerColor, animated: !ctx.hasHighlight || isHighlighted };
}

function buildEdges(
  globalsUsageMap: DataFlowDiagramProps['globalsUsageMap'],
  ctx: EdgeContext,
): Edge[] {
  const edges: Edge[] = [];
  const seen = new Set<string>();

  for (const [generatorId, usage] of globalsUsageMap.entries()) {
    if (!usage) continue;

    // Write edges: instance → key
    for (const ref of usage.writes) {
      const edgeId = `write-${generatorId}-${ref.key}`;
      if (seen.has(edgeId)) continue;
      seen.add(edgeId);

      const source = `instance-${generatorId}`;
      const target = `key-${ref.key}`;
      const { style, markerColor, animated } = resolveEdgeStyle(edgeId, source, target, ctx);

      edges.push({
        id: edgeId,
        source,
        target,
        sourceHandle: 'source',
        targetHandle: 'target',
        type: 'default',
        animated,
        style,
        markerEnd: { type: MarkerType.ArrowClosed, color: markerColor },
      });
    }

    // Read edges: key → instance
    for (const ref of usage.reads) {
      const edgeId = `read-${generatorId}-${ref.key}`;
      if (seen.has(edgeId)) continue;
      seen.add(edgeId);

      const source = `key-${ref.key}`;
      const target = `instance-${generatorId}`;
      const { style, markerColor, animated } = resolveEdgeStyle(edgeId, source, target, ctx);

      edges.push({
        id: edgeId,
        source,
        target,
        sourceHandle: 'source',
        targetHandle: 'target',
        type: 'default',
        animated,
        style,
        markerEnd: { type: MarkerType.ArrowClosed, color: markerColor },
      });
    }
  }

  return edges;
}

function computeDiagramHeight(instanceCount: number, keyCount: number): number {
  const maxCount = Math.max(instanceCount, keyCount);
  return Math.max(MIN_DIAGRAM_HEIGHT, maxCount * NODE_SPACING_Y + DIAGRAM_BOTTOM_PADDING);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DataFlowDiagram({
  scenarioEntries,
  generatorStatusMap,
  globalsUsageMap,
  highlightedNodeId,
  highlightedEdgeId,
  onInstanceClick,
}: Readonly<DataFlowDiagramProps>) {
  const nodeTypes = useMemo(
    () => ({ instance: InstanceNode, key: KeyNode }),
    [],
  );

  const { structuralNodes, structuralEdges, containerHeight } = useMemo(() => {
    const keyList = collectGlobalKeys(globalsUsageMap);

    const instanceNodes = buildInstanceNodes(scenarioEntries, generatorStatusMap, null);
    const keyNodes = buildKeyNodes(keyList, null);

    const ctx: EdgeContext = { highlightedNodeId: null, highlightedEdgeId: null, hasHighlight: false };
    const flowEdges = buildEdges(globalsUsageMap, ctx);

    return {
      structuralNodes: [...instanceNodes, ...keyNodes],
      structuralEdges: flowEdges,
      containerHeight: computeDiagramHeight(scenarioEntries.length, keyList.length),
    };
  }, [scenarioEntries, generatorStatusMap, globalsUsageMap]);

  const nodes = useMemo(
    () =>
      structuralNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          highlighted: highlightedNodeId === node.id,
        },
        style: {
          ...node.style,
          opacity: highlightedNodeId && node.id !== highlightedNodeId ? 0.3 : 1,
        },
      })),
    [structuralNodes, highlightedNodeId],
  );

  const edges = useMemo(
    () =>
      structuralEdges.map((edge) => ({
        ...edge,
        style: {
          ...edge.style,
          opacity: highlightedEdgeId && edge.id !== highlightedEdgeId ? 0.15 : 1,
          stroke:
            edge.id === highlightedEdgeId
              ? 'var(--mantine-primary-color-filled)'
              : edge.style?.stroke,
        },
        animated: highlightedEdgeId ? edge.id === highlightedEdgeId : edge.animated,
      })),
    [structuralEdges, highlightedEdgeId],
  );

  function handleNodeClick(_: React.MouseEvent, node: Node) {
    if (node.type === 'instance') {
      onInstanceClick?.((node.data as InstanceNodeData).label);
    }
  }

  return (
    <Paper withBorder p="md">
      <Group gap="xs" mb="sm">
        <IconRoute size={18} />
        <Title order={5} fw="normal">Data Flow</Title>
      </Group>
      <style>{REACT_FLOW_CONTROLS_CSS}</style>
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
