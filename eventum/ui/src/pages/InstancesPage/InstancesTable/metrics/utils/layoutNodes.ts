import { MarkerType, type Edge, type Node } from '@xyflow/react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

const COLUMN_X = [0, 350, 700] as const;
const NODE_SPACING_Y = 100;
const PADDING_TOP = 0;
const DIAGRAM_BOTTOM_PADDING = 60;
const MIN_GRAPH_HEIGHT = 300;

export interface PipelineNodeData extends Record<string, unknown> {
  pluginName: string;
  pluginId: number;
  metrics: { label: string; value: number; isError?: boolean }[];
  eps: number;
  colorType: 'input' | 'event' | 'output';
}

function computeColumnY(count: number, maxCount: number, index: number): number {
  const offset = ((maxCount - count) * NODE_SPACING_Y) / 2;
  return PADDING_TOP + offset + index * NODE_SPACING_Y;
}

const EDGE_STYLE = {
  strokeDasharray: '5,5',
  stroke: 'var(--mantine-color-text)',
  strokeWidth: 2,
  opacity: 0.6,
} as const;

export function buildPipelineGraph(stats: GeneratorStats): {
  nodes: Node<PipelineNodeData>[];
  edges: Edge[];
} {
  const nodes: Node<PipelineNodeData>[] = [];
  const edges: Edge[] = [];

  const maxCount = Math.max(stats.input.length, 1, stats.output.length);

  // Input nodes
  for (const [i, plugin] of stats.input.entries()) {
    const id = `input-${plugin.plugin_id}`;
    const perPluginEps = stats.input.length > 0 ? stats.input_eps / stats.input.length : 0;

    nodes.push({
      id,
      type: 'pipelineNode',
      position: {
        x: COLUMN_X[0],
        y: computeColumnY(stats.input.length, maxCount, i),
      },
      data: {
        pluginName: plugin.plugin_name,
        pluginId: plugin.plugin_id,
        metrics: [{ label: 'Generated', value: plugin.generated }],
        eps: perPluginEps,
        colorType: 'input',
      },
    });

    edges.push({
      id: `edge-${id}-event`,
      source: id,
      target: 'event-0',
      type: 'smoothstep',
      style: EDGE_STYLE,
      markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--mantine-color-text)' },
      animated: true,
    });
  }

  // Event node
  const eventMetrics: PipelineNodeData['metrics'] = [
    { label: 'Produced', value: stats.event.produced },
    { label: 'Produce failed', value: stats.event.produce_failed, isError: stats.event.produce_failed > 0 },
  ];

  nodes.push({
    id: 'event-0',
    type: 'pipelineNode',
    position: {
      x: COLUMN_X[1],
      y: computeColumnY(1, maxCount, 0),
    },
    data: {
      pluginName: stats.event.plugin_name,
      pluginId: stats.event.plugin_id,
      metrics: eventMetrics,
      eps: stats.input_eps,
      colorType: 'event',
    },
  });

  // Output nodes
  for (const [i, plugin] of stats.output.entries()) {
    const id = `output-${plugin.plugin_id}`;
    const perPluginEps = stats.output.length > 0 ? stats.output_eps / stats.output.length : 0;

    const outputMetrics: PipelineNodeData['metrics'] = [
      { label: 'Written', value: plugin.written },
      { label: 'Format failed', value: plugin.format_failed, isError: plugin.format_failed > 0 },
      { label: 'Write failed', value: plugin.write_failed, isError: plugin.write_failed > 0 },
    ];

    nodes.push({
      id,
      type: 'pipelineNode',
      position: {
        x: COLUMN_X[2],
        y: computeColumnY(stats.output.length, maxCount, i),
      },
      data: {
        pluginName: plugin.plugin_name,
        pluginId: plugin.plugin_id,
        metrics: outputMetrics,
        eps: perPluginEps,
        colorType: 'output',
      },
    });

    edges.push({
      id: `edge-event-${id}`,
      source: 'event-0',
      target: id,
      type: 'smoothstep',
      style: EDGE_STYLE,
      markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--mantine-color-text)' },
      animated: true,
    });
  }

  return { nodes, edges };
}

export function computeGraphHeight(stats: GeneratorStats): number {
  const maxCount = Math.max(stats.input.length, 1, stats.output.length);
  return Math.max(MIN_GRAPH_HEIGHT, maxCount * NODE_SPACING_Y + DIAGRAM_BOTTOM_PADDING);
}
