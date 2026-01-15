import { Group, Indicator, Text } from '@mantine/core';
import { FC } from 'react';

import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { describeInstanceStatus } from '@/pages/InstancesPage/InstancesTable/common/instance-status';

interface InstanceStatusProps {
  status: GeneratorStatus;
}

export const InstanceStatus: FC<InstanceStatusProps> = ({ status }) => {
  const { text, color, processing } = describeInstanceStatus(status);
  return (
    <Group gap="xs">
      <Indicator
        color={color}
        position="middle-center"
        processing={processing}
        size="8px"
      />
      <Text size="sm">{text}</Text>
    </Group>
  );
};
