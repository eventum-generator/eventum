import { Button, Group, MantineSize, Stack, Text } from '@mantine/core';
import { Icon } from '@tabler/icons-react';
import { FC } from 'react';

interface AreaButtonProps {
  icon: Icon;
  name: string;
  description: string;
  onClick: () => void;
  h?: MantineSize | (string & {});
  gap?: MantineSize | (string & {});
}

export const AreaButton: FC<AreaButtonProps> = ({
  icon: ButtonIcon,
  name,
  description,
  onClick,
  h = '100px',
  gap = 'xs',
}) => {
  return (
    <Button variant="default" h={h} onClick={onClick}>
      <Stack gap={gap} align="center">
        <Group gap="xs">
          <ButtonIcon size={18} />
          {name}
        </Group>
        <Text fz="sm" c="dimmed">
          {description}
        </Text>
      </Stack>
    </Button>
  );
};
