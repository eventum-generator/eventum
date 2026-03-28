import { Group, Paper, Title } from '@mantine/core';
import { IconRoute } from '@tabler/icons-react';
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FC, useMemo } from 'react';

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

interface PipelineGraphProps {
  stats: GeneratorStats;
}

export const PipelineGraph: FC<PipelineGraphProps> = ({ stats }) => {
  const { nodes, edges } = useMemo(() => buildPipelineGraph(stats), [stats]);
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
      <div style={{ height: graphHeight }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.5 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          preventScrolling={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </Paper>
  );
};
