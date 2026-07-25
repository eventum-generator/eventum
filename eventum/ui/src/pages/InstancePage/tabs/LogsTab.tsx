import { FC } from 'react';

import { streamGeneratorLogs } from '@/api/routes/generators';
import { LogsModal } from '@/components/modals/LogsModal';

/**
 * Logs tab - the streaming log viewer offered as a quick action from the
 * instances table, embedded here and sized to the page. Mounted on demand,
 * so the log socket opens when the tab opens and closes when it closes.
 */
export const LogsTab: FC<{ instanceId: string }> = ({ instanceId }) => (
  <LogsModal
    getWebSocket={() => streamGeneratorLogs(instanceId, 10_048_576)}
    height="calc(100vh - 300px)"
  />
);
