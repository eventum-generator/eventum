import { type Edge, MarkerType } from '@xyflow/react';

import { DataFlowDiagramProps } from './DataFlowDiagram';

/**
 * The model the data flow diagram is drawn from: which instance of a
 * scenario reaches which key of the shared state, in which direction,
 * and how tall the drawing has to be to hold them.
 *
 * Separate from the drawing because it is the part that can be wrong -
 * a flow that runs the wrong way, or one that is not there at all - and
 * the part that can be read without measuring anything.
 */

const PRIMARY_COLOR = 'var(--mantine-primary-color-filled)';
const TEXT_COLOR = 'var(--mantine-color-text)';

const NODE_SPACING_Y = 100;
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

export interface EdgeContext {
  highlightedNodeId: string | null | undefined;
  highlightedEdgeId: string | null | undefined;
  hasHighlight: boolean;
}

function resolveEdgeStyle(
  edgeId: string,
  sourceNodeId: string,
  targetNodeId: string,
  ctx: EdgeContext
) {
  const isHighlighted =
    ctx.highlightedEdgeId === edgeId ||
    sourceNodeId === ctx.highlightedNodeId ||
    targetNodeId === ctx.highlightedNodeId;

  const style = ctx.hasHighlight
    ? isHighlighted
      ? HIGHLIGHTED_EDGE_STYLE
      : DIMMED_EDGE_STYLE
    : BASE_EDGE_STYLE;

  const markerColor =
    ctx.hasHighlight && isHighlighted ? PRIMARY_COLOR : TEXT_COLOR;

  return { style, markerColor, animated: !ctx.hasHighlight || isHighlighted };
}

/**
 * The flows between the instances of a scenario and the keys they share.
 *
 * Exported because it is the model of the diagram: which instance reaches
 * which key, in which direction, and which of those flows the current
 * highlight leaves lit. The drawing on top of it is React Flow's.
 */
export function buildEdges(
  globalsUsageMap: DataFlowDiagramProps['globalsUsageMap'],
  ctx: EdgeContext
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
      const { style, markerColor, animated } = resolveEdgeStyle(
        edgeId,
        source,
        target,
        ctx
      );

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
      const { style, markerColor, animated } = resolveEdgeStyle(
        edgeId,
        source,
        target,
        ctx
      );

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

export function computeDiagramHeight(
  instanceCount: number,
  keyCount: number
): number {
  const maxCount = Math.max(instanceCount, keyCount);
  return Math.max(
    MIN_DIAGRAM_HEIGHT,
    maxCount * NODE_SPACING_Y + DIAGRAM_BOTTOM_PADDING
  );
}
