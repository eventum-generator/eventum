import { MarkerType, type Edge, type Node } from '@xyflow/react';

import type { GeneratorStats } from '@/api/routes/generators/schemas';

export const NODE_WIDTH = 250;
const COLUMN_GAP = 120;
const COLUMN_X = [0, NODE_WIDTH + COLUMN_GAP, (NODE_WIDTH + COLUMN_GAP) * 2] as const;

/** Fixed Y offset of edge handles from node top — all handles share this offset. */
export const HANDLE_Y = 20;

const NODE_SPACING_Y = 100;
const GRAPH_PADDING = 60;
const MIN_GRAPH_HEIGHT = 300;
const MAX_NODE_HEIGHT = 120;

export interface PipelineNodeData extends Record<string, unknown> {
  pluginName: string;
  pluginId: number;
  metrics: { label: string; value: number; isError?: boolean }[];
  colorType: 'input' | 'event' | 'output';
}

/**
 * Position nodes so their handle anchor points (at HANDLE_Y from top)
 * are evenly spaced and centered around `anchorY`.
 */
function layoutColumn(count: number, anchorY: number): number[] {
  const span = (count - 1) * NODE_SPACING_Y;
  const firstAnchor = anchorY - span / 2;
  return Array.from({ length: count }, (_, i) => firstAnchor + i * NODE_SPACING_Y - HANDLE_Y);
}

const EDGE_STYLE = {
  strokeDasharray: '5,5',
  stroke: 'var(--mantine-color-text)',
  strokeWidth: 2,
  opacity: 0.6,
} as const;

const MARKER_END = {
  type: MarkerType.ArrowClosed,
  color: 'var(--mantine-color-text)',
} as const;

/** Topology key — changes only when plugins are added / removed. */
export function structureKey(stats: GeneratorStats): string {
  const inputIds = stats.input.map((p) => p.plugin_id).join(',');
  const outputIds = stats.output.map((p) => p.plugin_id).join(',');
  return `${inputIds}|${stats.event.plugin_id}|${outputIds}`;
}

export function buildNodes(stats: GeneratorStats): Node<PipelineNodeData>[] {
  const maxCount = Math.max(stats.input.length, 1, stats.output.length);
  const anchorY = HANDLE_Y + ((maxCount - 1) * NODE_SPACING_Y) / 2;

  const inputYs = layoutColumn(stats.input.length, anchorY);
  const eventYs = layoutColumn(1, anchorY);
  const outputYs = layoutColumn(stats.output.length, anchorY);

  const nodes: Node<PipelineNodeData>[] = [];

  for (const [i, plugin] of stats.input.entries()) {
    nodes.push({
      id: `input-${plugin.plugin_id}`,
      type: 'pipelineNode',
      position: { x: COLUMN_X[0], y: inputYs[i]! },
      data: {
        pluginName: plugin.plugin_name,
        pluginId: plugin.plugin_id,
        metrics: [{ label: 'Generated', value: plugin.generated }],
        colorType: 'input',
      },
      width: NODE_WIDTH,
    });
  }

  nodes.push({
    id: 'event-0',
    type: 'pipelineNode',
    position: { x: COLUMN_X[1], y: eventYs[0]! },
    data: {
      pluginName: stats.event.plugin_name,
      pluginId: stats.event.plugin_id,
      metrics: [
        { label: 'Produced', value: stats.event.produced },
        { label: 'Dropped', value: stats.event.dropped },
        { label: 'Produce failed', value: stats.event.produce_failed, isError: stats.event.produce_failed > 0 },
      ],
      colorType: 'event',
    },
    width: NODE_WIDTH,
  });

  for (const [i, plugin] of stats.output.entries()) {
    nodes.push({
      id: `output-${plugin.plugin_id}`,
      type: 'pipelineNode',
      position: { x: COLUMN_X[2], y: outputYs[i]! },
      data: {
        pluginName: plugin.plugin_name,
        pluginId: plugin.plugin_id,
        metrics: [
          { label: 'Written', value: plugin.written },
          { label: 'Format failed', value: plugin.format_failed, isError: plugin.format_failed > 0 },
          { label: 'Write failed', value: plugin.write_failed, isError: plugin.write_failed > 0 },
        ],
        colorType: 'output',
      },
      width: NODE_WIDTH,
    });
  }

  return nodes;
}

export function buildEdges(stats: GeneratorStats): Edge[] {
  const edges: Edge[] = [];

  for (const plugin of stats.input) {
    const id = `input-${plugin.plugin_id}`;
    edges.push({
      id: `edge-${id}-event`,
      source: id,
      target: 'event-0',
      type: 'smoothstep',
      style: EDGE_STYLE,
      markerEnd: MARKER_END,
      animated: true,
    });
  }

  for (const plugin of stats.output) {
    const id = `output-${plugin.plugin_id}`;
    edges.push({
      id: `edge-event-${id}`,
      source: 'event-0',
      target: id,
      type: 'smoothstep',
      style: EDGE_STYLE,
      markerEnd: MARKER_END,
      animated: true,
    });
  }

  return edges;
}

/** Update only metrics inside existing nodes — positions untouched. */
export function updateNodesData(
  nodes: Node<PipelineNodeData>[],
  stats: GeneratorStats,
): Node<PipelineNodeData>[] {
  return nodes.map((node) => {
    const { data } = node;

    switch (data.colorType) {
      case 'input': {
        const plugin = stats.input.find((p) => p.plugin_id === data.pluginId);
        if (!plugin) return node;
        return {
          ...node,
          data: {
            ...data,
            metrics: [{ label: 'Generated', value: plugin.generated }],
          },
        };
      }
      case 'event':
        return {
          ...node,
          data: {
            ...data,
            metrics: [
              { label: 'Produced', value: stats.event.produced },
              { label: 'Dropped', value: stats.event.dropped },
              { label: 'Produce failed', value: stats.event.produce_failed, isError: stats.event.produce_failed > 0 },
            ],
          },
        };
      case 'output': {
        const plugin = stats.output.find((p) => p.plugin_id === data.pluginId);
        if (!plugin) return node;
        return {
          ...node,
          data: {
            ...data,
            metrics: [
              { label: 'Written', value: plugin.written },
              { label: 'Format failed', value: plugin.format_failed, isError: plugin.format_failed > 0 },
              { label: 'Write failed', value: plugin.write_failed, isError: plugin.write_failed > 0 },
            ],
          },
        };
      }
    }
  });
}

export function computeGraphHeight(stats: GeneratorStats): number {
  const maxCount = Math.max(stats.input.length, 1, stats.output.length);
  return Math.max(MIN_GRAPH_HEIGHT, (maxCount - 1) * NODE_SPACING_Y + MAX_NODE_HEIGHT + GRAPH_PADDING);
}
