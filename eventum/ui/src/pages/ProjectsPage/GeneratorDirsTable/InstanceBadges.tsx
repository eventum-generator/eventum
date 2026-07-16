import { Badge, Group, Text } from '@mantine/core';
import { FC, useMemo } from 'react';
import { Link } from 'react-router-dom';

import { useGenerators } from '@/api/hooks/useGenerators';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { statusDotColor } from '@/components/ui/statusPalette';
import { ROUTE_PATHS } from '@/routing/paths';

const MAX_SHOWN = 3;

function Dot({ color }: Readonly<{ color: string }>) {
  return (
    <span
      style={{
        display: 'block',
        width: 7,
        height: 7,
        borderRadius: '50%',
        background: color,
      }}
    />
  );
}

/**
 * Instance chips for a project row. Each chip links to that instance's page
 * and carries an activity dot colored by the instance status. The overflow
 * counter is not a link; its dot lights up when a hidden instance is running.
 * An empty list renders a muted marker.
 */
export const InstanceBadges: FC<{ ids: string[] }> = ({ ids }) => {
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
        Not used
      </Text>
    );
  }

  const shown = ids.slice(0, MAX_SHOWN);
  const hidden = ids.slice(MAX_SHOWN);
  const hiddenHasRunning = hidden.some((id) => statusById.get(id)?.is_running);

  return (
    <Group gap="xs">
      {shown.map((id) => {
        const status = statusById.get(id);
        return (
          <Badge
            key={id}
            component={Link}
            to={`${ROUTE_PATHS.INSTANCES}/${id}`}
            className="ev-instance-chip"
            variant="default"
            leftSection={
              <Dot
                color={status ? statusDotColor(status) : 'var(--ev-faint)'}
              />
            }
          >
            {id}
          </Badge>
        );
      })}
      {hidden.length > 0 && (
        <Badge
          className="ev-instance-chip ev-chip-more"
          variant="default"
          leftSection={
            hiddenHasRunning ? <Dot color="var(--ev-good)" /> : undefined
          }
        >
          +{hidden.length}
        </Badge>
      )}
    </Group>
  );
};
