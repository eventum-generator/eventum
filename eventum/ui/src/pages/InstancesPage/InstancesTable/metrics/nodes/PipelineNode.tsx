import { Group, Indicator, Paper, Text } from '@mantine/core';
import { Handle, type Node, type NodeProps, Position } from '@xyflow/react';
import { memo, useCallback, useEffect, useRef, useState } from 'react';

import { type PipelineNodeData } from '../utils/layoutNodes';
import { PLUGINS_INFO } from '@/api/routes/generator-configs/modules/plugins/registry';

type PipelineNodeType = Node<PipelineNodeData, 'pipelineNode'>;

const HIDDEN_HANDLE_STYLE = {
  background: 'transparent',
  border: 'none',
  width: 6,
  height: 6,
} as const;

function getPluginIcon(colorType: PipelineNodeData['colorType'], pluginName: string) {
  const registry = PLUGINS_INFO[colorType];
  const info = (registry as Record<string, { icon: React.ComponentType<{ size?: number }> }>)[pluginName];
  return info?.icon;
}

/** Blink interval in ms from EPS, clamped to [200ms, 3000ms]. */
function epsToInterval(eps: number): number {
  if (eps <= 0) return 0;
  return Math.min(3000, Math.max(200, 1000 / eps));
}

export const PipelineNode = memo(function PipelineNode({
  data,
}: NodeProps<PipelineNodeType>) {
  const Icon = getPluginIcon(data.colorType, data.pluginName);
  const [blinking, setBlinking] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const blink = useCallback(() => {
    setBlinking(true);
    setTimeout(() => setBlinking(false), 100);
  }, []);

  // Blink in sync with EPS — interval = 1000/eps ms
  useEffect(() => {
    clearInterval(intervalRef.current);

    const interval = epsToInterval(data.eps);
    if (interval <= 0) return;

    intervalRef.current = setInterval(blink, interval);
    return () => clearInterval(intervalRef.current);
  }, [data.eps, blink]);

  return (
    <Paper
      withBorder
      p="xs"
      style={{ minWidth: 160, borderStyle: 'solid' }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={HIDDEN_HANDLE_STYLE}
        isConnectable={false}
      />

      <Group gap={8} wrap="nowrap" mb={4}>
        {Icon && <Icon size={14} />}
        <Text size="sm" fw={500}>
          {data.pluginName} #{data.pluginId}
        </Text>
        <Indicator
          color={blinking ? 'green' : 'gray'}
          size={8}
          position="middle-center"
          processing={false}
          ml="auto"
        />
      </Group>

      {data.metrics.map((metric) => (
        <Group key={metric.label} gap="xs" justify="space-between">
          <Text size="xs" c="dimmed">
            {metric.label}
          </Text>
          <Text size="xs" fw={600} c={metric.isError ? 'red' : undefined}>
            {metric.value}
          </Text>
        </Group>
      ))}

      <Handle
        type="source"
        position={Position.Right}
        style={HIDDEN_HANDLE_STYLE}
        isConnectable={false}
      />
    </Paper>
  );
});
PipelineNode.displayName = 'PipelineNode';
