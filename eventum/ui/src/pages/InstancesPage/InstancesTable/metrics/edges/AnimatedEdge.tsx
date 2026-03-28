import {
  BaseEdge,
  type Edge,
  type EdgeProps,
  getBezierPath,
} from '@xyflow/react';
import { memo } from 'react';

import classes from './AnimatedEdge.module.css';

interface AnimatedEdgeData extends Record<string, unknown> {
  eps: number;
}

type AnimatedEdgeType = Edge<AnimatedEdgeData, 'animatedEdge'>;

function computeFlowDuration(eps: number): string {
  if (eps <= 0) return '0s';
  const duration = Math.min(4, Math.max(0.8, 2 / eps));
  return `${duration}s`;
}

export const AnimatedEdge = memo(function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<AnimatedEdgeType>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const eps = data?.eps ?? 0;
  const isAnimated = eps > 0;
  const flowDuration = computeFlowDuration(eps);

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: 'var(--mantine-color-default-border)',
          strokeWidth: 1.5,
          opacity: 0.6,
        }}
      />

      {isAnimated && (
        <circle
          className={classes.dot}
          data-animated
          style={{
            '--flow-duration': flowDuration,
            offsetPath: `path("${edgePath}")`,
          } as React.CSSProperties}
        />
      )}

      <text
        x={labelX}
        y={labelY - 10}
        className={classes.label}
        textAnchor="middle"
        dominantBaseline="auto"
      >
        {eps > 0 ? `${eps.toFixed(2)} eps` : ''}
      </text>
    </>
  );
});
