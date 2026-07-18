import { Badge, Group, Text } from '@mantine/core';
import { FC, useMemo } from 'react';
import { Link } from 'react-router-dom';

import { StatusDot } from './StatusDot';
import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { ROUTE_PATHS } from '@/routing/paths';

const DEFAULT_MAX_SHOWN = 3;

// Synthetic status for the overflow badge's dot: it does not represent one
// real instance, only the fact that at least one hidden instance is running.
const RUNNING_STATUS: GeneratorStatus = {
  is_initializing: false,
  is_running: true,
  is_stopping: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
};

interface InstanceBadgesProps {
  ids: string[];
  /** Where the overflow "+N" chip links. When set, the chip is a link (e.g.
   *  to a filtered instances table or the owning scenario); when omitted it is
   *  a static counter. Individual chips always link to their instance. */
  moreTo?: string;
  /** How many chips to show before collapsing the rest into "+N". */
  max?: number;
  /** Text rendered when the list is empty. */
  emptyText?: string;
}

/**
 * Instance chips for a table row. Each chip links to its instance page and
 * carries an activity dot colored by the instance status. The overflow counter
 * collapses the remainder; its dot lights up when a hidden instance is running,
 * and it becomes a link when `moreTo` is given. An empty list renders a muted
 * marker.
 */
export const InstanceBadges: FC<InstanceBadgesProps> = ({
  ids,
  moreTo,
  max = DEFAULT_MAX_SHOWN,
  emptyText = 'Not used',
}) => {
  const { data: generators } = useGenerators();

  const statusById = useMemo(() => {
    const map = new Map<string, GeneratorStatus>();
    for (const generator of generators ?? []) {
      map.set(generator.id, generator.status);
    }
    return map;
  }, [generators]);

  if (ids.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        {emptyText}
      </Text>
    );
  }

  const shown = ids.slice(0, max);
  const hidden = ids.slice(max);
  const hiddenHasRunning = hidden.some((id) => statusById.get(id)?.is_running);
  const moreDot = hiddenHasRunning ? (
    <StatusDot status={RUNNING_STATUS} />
  ) : undefined;

  return (
    <Group gap="xs">
      {shown.map((id) => (
        <Badge
          key={id}
          component={Link}
          to={`${ROUTE_PATHS.INSTANCES}/${id}`}
          className="ev-instance-chip"
          variant="default"
          leftSection={<StatusDot status={statusById.get(id)} />}
        >
          {id}
        </Badge>
      ))}
      {hidden.length > 0 &&
        (moreTo ? (
          <Badge
            component={Link}
            to={moreTo}
            className="ev-instance-chip ev-chip-more"
            variant="default"
            leftSection={moreDot}
          >
            +{hidden.length}
          </Badge>
        ) : (
          <Badge
            className="ev-instance-chip ev-chip-more"
            variant="default"
            leftSection={moreDot}
          >
            +{hidden.length}
          </Badge>
        ))}
    </Group>
  );
};
