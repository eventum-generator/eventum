import {
  DefaultMantineColor,
  Flex,
  Group,
  Paper,
  Stack,
  StyleProp,
  Text,
  Title,
} from '@mantine/core';
import {
  Icon,
  IconAlertTriangle,
  IconBox,
  IconPlayerPlay,
  IconPower,
  IconProps,
} from '@tabler/icons-react';
import { FC, ReactNode } from 'react';

import { GeneratorsInfo } from '@/api/routes/generators/schemas';

interface InstancesStatusesPanelProps {
  generators: GeneratorsInfo;
}

export const InstancesStatusesPanel: FC<InstancesStatusesPanelProps> = ({
  generators,
}) => {
  const metrics: {
    content: ReactNode;
    caption: ReactNode;
    icon: React.ForwardRefExoticComponent<
      IconProps & React.RefAttributes<Icon>
    >;
    iconColor: StyleProp<DefaultMantineColor>;
  }[] = [
    {
      content: generators.length,
      caption: 'Total',
      icon: IconBox,
      iconColor: 'primary',
    },
    {
      content: generators.filter((generator) => generator.status.is_running)
        .length,
      caption: 'Active',
      icon: IconPlayerPlay,
      iconColor: 'green.4',
    },
    {
      content: generators.filter(
        (generator) =>
          !generator.status.is_running &&
          (!generator.status.is_ended_up ||
            generator.status.is_ended_up_successfully)
      ).length,
      caption: 'Inactive',
      icon: IconPower,
      iconColor: 'gray.6',
    },
    {
      content: generators.filter(
        (generator) =>
          generator.status.is_ended_up &&
          !generator.status.is_ended_up_successfully
      ).length,
      caption: 'Failed',
      icon: IconAlertTriangle,
      iconColor: 'red.6',
    },
  ];

  return (
    <Paper withBorder shadow="sm" p="md">
      <Stack gap="xs">
        <Title order={4} fw="500">
          Instances
        </Title>

        <Group grow gap="xs" align="start">
          {metrics.map((panel, index) => (
            <Stack key={index} gap="2px" justify="center" align="center">
              <Title order={2} fw="500">
                {panel.content}
              </Title>
              <Group align="center" gap="6px" wrap="nowrap" mr={'10px'}>
                <Flex c={panel.iconColor} align="center">
                  <panel.icon size={20} />
                </Flex>
                <Text size="sm">{panel.caption}</Text>
              </Group>
            </Stack>
          ))}
        </Group>
      </Stack>
    </Paper>
  );
};
