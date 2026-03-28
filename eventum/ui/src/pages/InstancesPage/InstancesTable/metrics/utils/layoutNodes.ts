import type { Edge, Node } from '@xyflow/react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

const COLUMN_X = [0, 350, 700] as const;
const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;
const NODE_SPACING_Y = 100;
const PADDING_TOP = 30;

export interface PipelineNodeData extends Record<string, unknown> {
  pluginName: string;
  pluginId: number;
  metrics: { label: string; value: number; isError?: boolean }[];
  eps: number;
  colorType: 'input' | 'event' | 'output';
}

function computeColumnY(count: number, index: number): number {
  const totalHeight = (count - 1) * NODE_SPACING_Y;
  const startY = PADDING_TOP + (Math.max(totalHeight, 0) - totalHeight) / 2;
  return startY + index * NODE_SPACING_Y;
}

export function buildPipelineGraph(stats: GeneratorStats): {
  nodes: Node<PipelineNodeData>[];
  edges: Edge[];
} {
  const nodes: Node<PipelineNodeData>[] = [];
  const edges: Edge[] = [];

  const maxCount = Math.max(stats.input.length, 1, stats.output.length);

  // Input nodes
  stats.input.forEach((plugin, i) => {
    const id = `input-${plugin.plugin_id}`;
    nodes.push({
      id,
      type: 'pipelineNode',
      position: {
        x: COLUMN_X[0],
        y:
          computeColumnY(stats.input.length, i) +
          ((maxCount - stats.input.length) * NODE_SPACING_Y) / 2,
      },
      data: {
        pluginName: plugin.plugin_name,
        pluginId: plugin.plugin_id,
        metrics: [{ label: 'Generated', value: plugin.generated }],
        eps: stats.input_eps / stats.input.length,
        colorType: 'input',
      },
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    });

    edges.push({
      id: `edge-${id}-event`,
      source: id,
      target: 'event-0',
      type: 'animatedEdge',
      data: { eps: stats.input_eps },
    });
  });

  // Event node
  const eventMetrics: PipelineNodeData['metrics'] = [
    { label: 'Produced', value: stats.event.produced },
  ];
  if (stats.event.produce_failed > 0) {
    eventMetrics.push({
      label: 'Failed',
      value: stats.event.produce_failed,
      isError: true,
    });
  }

  nodes.push({
    id: 'event-0',
    type: 'pipelineNode',
    position: {
      x: COLUMN_X[1],
      y:
        computeColumnY(1, 0) + ((maxCount - 1) * NODE_SPACING_Y) / 2,
    },
    data: {
      pluginName: stats.event.plugin_name,
      pluginId: stats.event.plugin_id,
      metrics: eventMetrics,
      eps: stats.input_eps,
      colorType: 'event',
    },
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
  });

  // Output nodes
  stats.output.forEach((plugin, i) => {
    const id = `output-${plugin.plugin_id}`;

    const outputMetrics: PipelineNodeData['metrics'] = [
      { label: 'Written', value: plugin.written },
    ];
    const totalFailed = plugin.format_failed + plugin.write_failed;
    if (totalFailed > 0) {
      outputMetrics.push({
        label: 'Failed',
        value: totalFailed,
        isError: true,
      });
    }

    nodes.push({
      id,
      type: 'pipelineNode',
      position: {
        x: COLUMN_X[2],
        y:
          computeColumnY(stats.output.length, i) +
          ((maxCount - stats.output.length) * NODE_SPACING_Y) / 2,
      },
      data: {
        pluginName: plugin.plugin_name,
        pluginId: plugin.plugin_id,
        metrics: outputMetrics,
        eps: stats.output_eps / stats.output.length,
        colorType: 'output',
      },
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    });

    edges.push({
      id: `edge-event-${id}`,
      source: 'event-0',
      target: id,
      type: 'animatedEdge',
      data: { eps: stats.output_eps },
    });
  });

  return { nodes, edges };
}
