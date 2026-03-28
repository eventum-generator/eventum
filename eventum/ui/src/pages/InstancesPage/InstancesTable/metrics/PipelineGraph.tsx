import { Group, Paper, Title } from '@mantine/core';
import { IconRoute } from '@tabler/icons-react';
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  useNodesInitialized,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FC, useEffect, useMemo, useRef } from 'react';

import { PipelineNode } from './nodes/PipelineNode';
import { buildPipelineGraph, computeGraphHeight } from './utils/layoutNodes';
import type { GeneratorStats } from '@/api/routes/generators/schemas';

const nodeTypes = { pipelineNode: PipelineNode } as const;

const TEXT_COLOR = 'var(--mantine-color-text)';

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

/** Calls fitView once after all nodes have been measured by the browser. */
function FitViewOnReady() {
  const { fitView } = useReactFlow();
  const nodesInitialized = useNodesInitialized();

  useEffect(() => {
    if (nodesInitialized) {
      fitView({ padding: 0.3 });
    }
  }, [nodesInitialized, fitView]);

  return null;
}

/** Build a structural key from plugin IDs to detect topology changes. */
function structureKey(stats: GeneratorStats): string {
  const inputIds = stats.input.map((p) => p.plugin_id).join(',');
  const eventId = stats.event.plugin_id;
  const outputIds = stats.output.map((p) => p.plugin_id).join(',');
  return `${inputIds}|${eventId}|${outputIds}`;
}

interface PipelineGraphProps {
  stats: GeneratorStats;
}

export const PipelineGraph: FC<PipelineGraphProps> = ({ stats }) => {
  const prevKeyRef = useRef('');

  // Nodes update on every refetch (metrics change)
  // Edges only recreate when topology changes (plugins added/removed)
  const { nodes, edges } = useMemo(() => buildPipelineGraph(stats), [stats]);
  const stableEdges = useMemo(() => {
    const key = structureKey(stats);
    if (key === prevKeyRef.current) return undefined; // keep previous
    prevKeyRef.current = key;
    return edges;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats]);

  const edgesRef = useRef(edges);
  if (stableEdges !== undefined) {
    edgesRef.current = stableEdges;
  }

  const graphHeight = useMemo(() => computeGraphHeight(stats), [stats]);

  return (
    <Paper withBorder p="md">
      <Group gap="xs" mb="sm">
        <IconRoute size={18} />
        <Title order={5} fw="normal">
          Pipeline
        </Title>
      </Group>
      <style>{REACT_FLOW_CONTROLS_CSS}</style>
      <div style={{ height: graphHeight, maxHeight: '80vh' }}>
        <ReactFlow
          nodes={nodes}
          edges={edgesRef.current}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <FitViewOnReady />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} position="bottom-right" />
        </ReactFlow>
      </div>
    </Paper>
  );
};
