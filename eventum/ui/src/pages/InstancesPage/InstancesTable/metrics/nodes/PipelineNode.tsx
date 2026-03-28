import { Group, Paper, Text } from '@mantine/core';
import { Handle, type Node, type NodeProps, Position } from '@xyflow/react';
import { memo } from 'react';

import { type PipelineNodeData } from '../utils/layoutNodes';
import { PLUGINS_INFO } from '@/api/routes/generator-configs/modules/plugins/registry';

type PipelineNodeType = Node<PipelineNodeData, 'pipelineNode'>;

const HANDLE_STYLE = {
  background: 'transparent',
  border: 'none',
  width: 6,
  height: 6,
  top: 20,
} as const;

function getPluginIcon(colorType: PipelineNodeData['colorType'], pluginName: string) {
  const registry = PLUGINS_INFO[colorType];
  const info = (registry as Record<string, { icon: React.ComponentType<{ size?: number }> }>)[pluginName];
  return info?.icon;
}

export const PipelineNode = memo(function PipelineNode({
  data,
}: NodeProps<PipelineNodeType>) {
  const Icon = getPluginIcon(data.colorType, data.pluginName);

  return (
    <Paper
      withBorder
      p="xs"
      style={{ width: 250, borderStyle: 'solid' }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={HANDLE_STYLE}
        isConnectable={false}
      />

      <Group gap={8} wrap="nowrap" mb={4}>
        {Icon && <Icon size={14} />}
        <Text size="sm" fw={500}>
          {data.pluginName} #{data.pluginId}
        </Text>
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
        style={HANDLE_STYLE}
        isConnectable={false}
      />
    </Paper>
  );
});
PipelineNode.displayName = 'PipelineNode';
