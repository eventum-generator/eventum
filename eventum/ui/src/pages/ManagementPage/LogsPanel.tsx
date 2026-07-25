import { Paper, Stack } from '@mantine/core';
import { FC } from 'react';

import { SectionLabel } from './primitives';
import { streamInstanceLogs } from '@/api/routes/instance';
import { LogsModal } from '@/components/modals/LogsModal';

/**
 * The application's main log, streamed live and embedded in the page rather
 * than hidden behind a modal, so it is visible the moment the page opens.
 */
export const LogsPanel: FC = () => (
  <Stack gap="xs">
    <SectionLabel>Instance logs</SectionLabel>
    <Paper withBorder p="sm">
      <LogsModal
        getWebSocket={() => streamInstanceLogs(10_048_576)}
        height="420px"
      />
    </Paper>
  </Stack>
);
