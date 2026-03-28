import { Group, Paper, Title } from '@mantine/core';
import { IconRoute } from '@tabler/icons-react';
import {
  Background,
  BackgroundVariant,
  Controls,
  type Node,
  ReactFlow,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FC, useEffect, useMemo, useRef, useState } from 'react';

import { PipelineNode } from './nodes/PipelineNode';
import {
  type PipelineNodeData,
  buildEdges,
  buildNodes,
  computeGraphHeight,
  structureKey,
  updateNodesData,
} from './utils/layoutNodes';
import type { GeneratorStats } from '@/api/routes/generators/schemas';

const nodeTypes = { pipelineNode: PipelineNode } as const;

const TEXT_COLOR = 'var(--mantine-color-text)';
const FIT_PADDING = 0.2;

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

/**
 * Updates only node DATA via setNodes callback — positions stay untouched,
 * so ReactFlow does not recalculate edge paths and CSS animations keep running.
 */
function NodeDataUpdater({ stats, topoKey }: { stats: GeneratorStats; topoKey: string }) {
  const { setNodes, setEdges, fitView } = useReactFlow();
  const prevTopoRef = useRef(topoKey);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    if (topoKey !== prevTopoRef.current) {
      prevTopoRef.current = topoKey;
      setNodes(buildNodes(stats));
      setEdges(buildEdges(stats));
      timeoutId = setTimeout(() => fitView({ padding: FIT_PADDING }), 50);
    } else {
      setNodes((nodes) => updateNodesData(nodes as Node<PipelineNodeData>[], stats));
    }

    return () => { if (timeoutId) clearTimeout(timeoutId); };
  }, [stats, topoKey, setNodes, setEdges, fitView]);

  return null;
}

interface PipelineGraphProps {
  stats: GeneratorStats;
}

export const PipelineGraph: FC<PipelineGraphProps> = ({ stats }) => {
  const topoKey = structureKey(stats);
  const fitIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Used once on mount — subsequent updates go through NodeDataUpdater
  const [initialNodes] = useState(() => buildNodes(stats));
  const [initialEdges] = useState(() => buildEdges(stats));

  const graphHeight = useMemo(() => computeGraphHeight(stats), [stats]);

  useEffect(() => {
    return () => {
      if (fitIntervalRef.current) clearInterval(fitIntervalRef.current);
    };
  }, []);

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
          defaultNodes={initialNodes}
          defaultEdges={initialEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: FIT_PADDING }}
          onInit={(instance) => {
            let attempts = 0;
            fitIntervalRef.current = setInterval(() => {
              instance.fitView({ padding: FIT_PADDING });
              if (++attempts >= 5 && fitIntervalRef.current) {
                clearInterval(fitIntervalRef.current);
                fitIntervalRef.current = null;
              }
            }, 200);
          }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <NodeDataUpdater stats={stats} topoKey={topoKey} />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} position="bottom-right" />
        </ReactFlow>
      </div>
    </Paper>
  );
};
