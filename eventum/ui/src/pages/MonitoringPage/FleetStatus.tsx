import { FC } from 'react';

import { GeneratorsInfo } from '@/api/routes/generators/schemas';
import { InstanceStatusSummary } from '@/components/ui/InstanceStatusSummary';

interface FleetStatusProps {
  generators: GeneratorsInfo;
}

/** Compact fleet status for the monitoring header - shares the Home rail's
 *  active/inactive summary with the inactive breakdown. */
export const FleetStatus: FC<FleetStatusProps> = ({ generators }) => (
  <InstanceStatusSummary statuses={generators.map((g) => g.status)} />
);
