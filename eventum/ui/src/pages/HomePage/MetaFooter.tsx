import { Divider, Group, Stack, Text } from '@mantine/core';
import { FC } from 'react';

import { InstanceInfo } from '@/api/routes/instance/schemas';

interface MetaFooterProps {
  instanceInfo: InstanceInfo | undefined;
}

const Item: FC<{ label: string; value: string }> = ({ label, value }) => (
  <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
    <Text size="xs" c="dimmed" fw={600}>
      {label}
    </Text>
    <Text size="xs" c="dimmed" truncate>
      {value}
    </Text>
  </Group>
);

export const MetaFooter: FC<MetaFooterProps> = ({ instanceInfo }) => {
  if (!instanceInfo) {
    return null;
  }

  return (
    <Stack gap="sm">
      <Divider />
      <Group gap="xl" wrap="wrap">
        <Item label="Version" value={instanceInfo.app_version} />
        <Item label="Python" value={instanceInfo.python_version} />
        <Item label="Platform" value={instanceInfo.platform} />
      </Group>
    </Stack>
  );
};
