import { Group, Paper, SegmentedControl, Stack } from '@mantine/core';
import { FC, useState } from 'react';

import { SectionLabel } from './primitives';
import { streamInstanceLogs } from '@/api/routes/instance';
import { InstanceLogChannel } from '@/api/routes/instance/schemas';
import { LogsModal } from '@/components/modals/LogsModal';

const CHANNELS: { value: InstanceLogChannel; label: string }[] = [
  { value: 'main', label: 'Main' },
  { value: 'server', label: 'Server' },
  { value: 'server_access', label: 'Access' },
  { value: 'mcp', label: 'MCP' },
];

/**
 * The application's logs, streamed live and embedded in the page rather than
 * hidden behind a modal, so they are visible the moment the page opens. Each
 * channel is a separate stream, so switching remounts the viewer to open the
 * socket of the selected one.
 */
export const LogsPanel: FC = () => {
  const [channel, setChannel] = useState<InstanceLogChannel>('main');

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="center">
        <SectionLabel>Instance logs</SectionLabel>
        <SegmentedControl
          data={CHANNELS}
          value={channel}
          onChange={(value) => setChannel(value as InstanceLogChannel)}
        />
      </Group>
      <Paper withBorder p="sm">
        <LogsModal
          key={channel}
          getWebSocket={() => streamInstanceLogs(channel, 10_048_576)}
          height="420px"
        />
      </Paper>
    </Stack>
  );
};
