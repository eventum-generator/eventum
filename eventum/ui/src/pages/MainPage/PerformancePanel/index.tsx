import { Divider, Flex, Group, Paper, Stack, Text, Title } from '@mantine/core';
import {
  IconArrowNarrowDown,
  IconArrowNarrowUp,
  IconCpu,
  IconDatabase,
  IconFileDownload,
  IconFileUpload,
  IconNetwork,
  IconTopologyBus,
} from '@tabler/icons-react';
import bytes from 'bytes';
import { FC } from 'react';

import { PerformanceDonutChart } from './PerformanceDonutChart';
import { InstanceInfo } from '@/api/routes/instance/schemas';

interface PerformancePanelProps {
  instanceInfo: InstanceInfo;
}

export const PerformancePanel: FC<PerformancePanelProps> = ({
  instanceInfo,
}) => {
  return (
    <Paper withBorder shadow="sm" p="md">
      <Stack gap="4px">
        <Title order={4} fw="500">
          Performance
        </Title>

        <Group gap="xs" justify="space-evenly" my="md">
          <PerformanceDonutChart
            data={[
              {
                name: 'Used',
                value: instanceInfo.memory_used_bytes,
                color: 'primary',
              },
              {
                name: 'Available',
                value: instanceInfo.memory_available_bytes,
                color: 'gray.6',
              },
            ]}
            chartLabel={
              Math.round(
                (instanceInfo.memory_used_bytes /
                  instanceInfo.memory_total_bytes) *
                  100
              ).toString() + '%'
            }
            valueFormatter={(value) => bytes(value) ?? '-'}
            rightSection={
              <Stack gap="2px">
                <Text size="sm" ta="center">
                  {bytes(instanceInfo.memory_used_bytes)} /{' '}
                  {bytes(instanceInfo.memory_total_bytes)}
                </Text>
                <Divider />
                <Group gap="4px">
                  <IconTopologyBus
                    size={18}
                    style={{ transform: 'rotate(180deg)' }}
                  />
                  <Text size="sm" ta="center">
                    Memory usage
                  </Text>
                </Group>
              </Stack>
            }
          />

          <PerformanceDonutChart
            data={[
              {
                name: 'Used',
                value: instanceInfo.cpu_percent,
                color: 'primary',
              },
              {
                name: 'Available',
                value: 100 - instanceInfo.cpu_percent,
                color: 'gray.6',
              },
            ]}
            chartLabel={Math.round(instanceInfo.cpu_percent).toString() + '%'}
            rightSection={
              <Stack gap="2px">
                <Text size="sm" ta="center">
                  {instanceInfo.cpu_count}
                  {' x '}
                  {Math.round(instanceInfo.cpu_frequency_mhz).toString()} MHz
                </Text>
                <Divider />
                <Group gap="4px">
                  <IconCpu size={15} />
                  <Text size="sm" ta="center">
                    CPU usage
                  </Text>
                </Group>
              </Stack>
            }
          />

          <PerformanceDonutChart
            data={[
              {
                name: 'Sent',
                value: instanceInfo.network_sent_bytes,
                color: 'yellow.6',
              },
              {
                name: 'Received',
                value: instanceInfo.network_received_bytes,
                color: 'green.6',
              },
            ]}
            valueFormatter={(value) => bytes(value) ?? '-'}
            rightSection={
              <Stack gap="2px">
                <Group gap="2px">
                  <Group gap="0" title="received">
                    <Flex c="green.6">
                      <IconArrowNarrowDown size={15} />
                    </Flex>
                    <Text size="sm" ta="center">
                      {bytes(instanceInfo.network_received_bytes) ?? '-'}
                    </Text>
                  </Group>
                  <Group gap="0" title="sent">
                    <Flex c="yellow.6">
                      <IconArrowNarrowUp size={15} />
                    </Flex>
                    <Text size="sm" ta="center">
                      {bytes(instanceInfo.network_sent_bytes) ?? '-'}
                    </Text>
                  </Group>
                </Group>
                <Divider />
                <Group gap="4px">
                  <IconNetwork size={15} />
                  <Text size="sm" ta="center">
                    Network usage
                  </Text>
                </Group>
              </Stack>
            }
          />

          <PerformanceDonutChart
            data={[
              {
                name: 'Written',
                value: instanceInfo.disk_written_bytes,
                color: 'yellow.6',
              },
              {
                name: 'Read',
                value: instanceInfo.disk_read_bytes,
                color: 'green.6',
              },
            ]}
            valueFormatter={(value) => bytes(value) ?? '-'}
            rightSection={
              <Stack gap="2px">
                <Group gap="4px">
                  <Group gap="2px" title="written">
                    <Flex c="yellow.6">
                      <IconFileDownload size={15} />
                    </Flex>
                    <Text size="sm" ta="center">
                      {bytes(instanceInfo.disk_written_bytes) ?? '-'}
                    </Text>
                  </Group>
                  <Group gap="2px" title="read">
                    <Flex c="green.6">
                      <IconFileUpload size={15} />
                    </Flex>

                    <Text size="sm" ta="center">
                      {bytes(instanceInfo.disk_read_bytes) ?? '-'}
                    </Text>
                  </Group>
                </Group>
                <Divider />
                <Group gap="4px">
                  <IconDatabase size={15} />
                  <Text size="sm" ta="center">
                    Disk usage
                  </Text>
                </Group>
              </Stack>
            }
          />
        </Group>
      </Stack>
    </Paper>
  );
};
