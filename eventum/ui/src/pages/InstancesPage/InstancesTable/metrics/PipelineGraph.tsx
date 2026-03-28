import { ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FC, useMemo } from 'react';

import { AnimatedEdge } from './edges/AnimatedEdge';
import { PipelineNode } from './nodes/PipelineNode';
import { buildPipelineGraph, computeGraphHeight } from './utils/layoutNodes';
import type { GeneratorStats } from '@/api/routes/generators/schemas';

const nodeTypes = { pipelineNode: PipelineNode } as const;
const edgeTypes = { animatedEdge: AnimatedEdge } as const;

interface PipelineGraphProps {
  stats: GeneratorStats;
}

export const PipelineGraph: FC<PipelineGraphProps> = ({ stats }) => {
  const { nodes, edges } = useMemo(() => buildPipelineGraph(stats), [stats]);
  const graphHeight = useMemo(() => computeGraphHeight(stats), [stats]);

  return (
    <div style={{ width: '100%', height: graphHeight }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
        proOptions={{ hideAttribution: true }}
      />
    </div>
  );
};
