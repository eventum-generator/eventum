import { Handle, type Node, type NodeProps, Position } from '@xyflow/react';
import { memo } from 'react';

import { computeAnimationDuration, type PipelineNodeData } from '../utils/layoutNodes';

import classes from './PipelineNode.module.css';

type PipelineNodeType = Node<PipelineNodeData, 'pipelineNode'>;

const HIDDEN_HANDLE_STYLE = {
  background: 'transparent',
  border: 'none',
  width: 6,
  height: 6,
} as const;

const NODE_COLORS = {
  input: { bg: '#1e3a5f', border: '#2a5a8f' },
  event: { bg: '#3b1f6e', border: '#6d3fc0' },
  output: { bg: '#0c4a4a', border: '#0ea5a5' },
} as const;

export const PipelineNode = memo(function PipelineNode({
  data,
}: NodeProps<PipelineNodeType>) {
  const pulseDuration = computeAnimationDuration(data.eps);
  const isAnimated = data.eps > 0;
  const colors = NODE_COLORS[data.colorType];

  return (
    <div
      className={classes.node}
      style={
        {
          '--node-bg': colors.bg,
          '--node-border': colors.border,
        } as React.CSSProperties
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        style={HIDDEN_HANDLE_STYLE}
      />

      <div className={classes.header}>
        <div
          className={classes.statusDot}
          data-animated={isAnimated}
          style={
            isAnimated
              ? ({ '--pulse-duration': pulseDuration } as React.CSSProperties)
              : undefined
          }
        />
        <span className={classes.name}>
          {data.pluginName} #{data.pluginId}
        </span>
      </div>

      {data.metrics.map((metric) => (
        <div key={metric.label} className={classes.metric}>
          <span>{metric.label}</span>
          <span
            className={
              metric.isError ? classes.metricValueError : classes.metricValue
            }
          >
            {metric.value}
          </span>
        </div>
      ))}

      <Handle
        type="source"
        position={Position.Right}
        style={HIDDEN_HANDLE_STYLE}
      />
    </div>
  );
});
