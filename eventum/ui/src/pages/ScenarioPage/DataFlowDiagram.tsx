import { Group, Paper, Stack, Text } from '@mantine/core';
import { IconDatabase, IconPlayerPlay, IconRoute } from '@tabler/icons-react';
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CSSProperties, memo, useMemo } from 'react';

import { SectionHeader } from './SectionHeader';
import { EdgeContext, buildEdges, computeDiagramHeight } from './data-flow';
import { collectGlobalKeys } from './globals-usage';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { REACT_FLOW_CONTROLS_CSS } from '@/components/ui/reactFlowControlsCss';
import {
  statusDotColor,
  statusDotGlowOrNone,
} from '@/components/ui/statusPalette';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DataFlowDiagramProps {
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
  statusGlow: string | undefined;
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

const PRIMARY_COLOR = 'var(--mantine-primary-color-filled)';

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
    <Handle
      type="source"
      position={Position.Right}
      id="source"
      style={SOURCE_HANDLE_STYLE}
      isConnectable={false}
    />
    <Handle
      type="target"
      position={Position.Right}
      id="target"
      style={TARGET_HANDLE_STYLE}
      isConnectable={false}
    />
    <Group gap={8} wrap="nowrap" pr={6} justify="space-between">
      <Group gap={8} wrap="nowrap">
        <IconPlayerPlay size={14} />
        <Text size="sm" fw={500}>
          {data.label}
        </Text>
      </Group>
      <span
        className="ev-status-dot"
        data-glow={!!data.statusGlow}
        data-processing={data.processing}
        style={
          {
            '--ev-dot-size': '8px',
            '--ev-dot': data.statusColor,
            '--ev-dot-glow': data.statusGlow,
          } as CSSProperties
        }
      />
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
    <Handle
      type="target"
      position={Position.Left}
      id="target"
      style={SOURCE_HANDLE_STYLE}
      isConnectable={false}
    />
    <Handle
      type="source"
      position={Position.Left}
      id="source"
      style={TARGET_HANDLE_STYLE}
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
  highlightedNodeId: string | null | undefined
): DiagramNode[] {
  return entries.map((entry, i) => {
    const status = statusMap.get(entry.id) ?? INACTIVE_STATUS;
    const { processing } = describeInstanceStatus(status);
    const nodeId = `instance-${entry.id}`;

    return {
      id: nodeId,
      type: 'instance' as const,
      position: { x: INSTANCE_X, y: i * NODE_SPACING_Y + PADDING_TOP },
      data: {
        label: entry.id,
        statusColor: statusDotColor(status),
        statusGlow: statusDotGlowOrNone(status),
        processing,
        highlighted: highlightedNodeId === nodeId,
      },
      draggable: false,
    };
  });
}

function buildKeyNodes(
  keys: string[],
  highlightedNodeId: string | null | undefined
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
    []
  );

  const { structuralNodes, structuralEdges, containerHeight } = useMemo(() => {
    const keyList = collectGlobalKeys(globalsUsageMap);

    const instanceNodes = buildInstanceNodes(
      scenarioEntries,
      generatorStatusMap,
      null
    );
    const keyNodes = buildKeyNodes(keyList, null);

    const ctx: EdgeContext = {
      highlightedNodeId: null,
      highlightedEdgeId: null,
      hasHighlight: false,
    };
    const flowEdges = buildEdges(globalsUsageMap, ctx);

    return {
      structuralNodes: [...instanceNodes, ...keyNodes],
      structuralEdges: flowEdges,
      containerHeight: computeDiagramHeight(
        scenarioEntries.length,
        keyList.length
      ),
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
    [structuralNodes, highlightedNodeId]
  );

  const edges = useMemo(
    () =>
      structuralEdges.map((edge) => ({
        ...edge,
        style: {
          ...edge.style,
          opacity:
            highlightedEdgeId && edge.id !== highlightedEdgeId ? 0.15 : 1,
          stroke:
            edge.id === highlightedEdgeId
              ? 'var(--mantine-primary-color-filled)'
              : edge.style?.stroke,
        },
        animated: highlightedEdgeId
          ? edge.id === highlightedEdgeId
          : edge.animated,
      })),
    [structuralEdges, highlightedEdgeId]
  );

  function handleNodeClick(_: React.MouseEvent, node: Node) {
    if (node.type === 'instance') {
      onInstanceClick?.((node.data as InstanceNodeData).label);
    }
  }

  return (
    <Paper withBorder p="md">
      <style>{REACT_FLOW_CONTROLS_CSS}</style>
      <Stack gap="sm">
        <SectionHeader icon={<IconRoute size={18} />} title="Data Flow" />
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
      </Stack>
    </Paper>
  );
}
