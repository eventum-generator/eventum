import { FC } from 'react';

import { InstanceMetrics } from '../../InstancesPage/InstancesTable/metrics/InstanceMetrics';

/**
 * Metrics tab - the same live per-plugin metrics view offered as a quick
 * action from the instances table, embedded here. Mounted on demand, so
 * polling starts when the tab opens and stops when it closes.
 */
export const MetricsTab: FC<{ instanceId: string }> = ({ instanceId }) => (
  <InstanceMetrics instanceId={instanceId} />
);
