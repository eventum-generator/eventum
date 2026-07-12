import { Badge, Group, Text } from '@mantine/core';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import { ROUTE_PATHS } from '@/routing/paths';

const MAX_SHOWN = 3;

/**
 * Instance chips for a project row. Each chip links to that instance's page;
 * the overflow counter is not a link. An empty list renders a muted marker.
 */
export const InstanceBadges: FC<{ ids: string[] }> = ({ ids }) => {
  if (ids.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Not used
      </Text>
    );
  }

  const shown = ids.slice(0, MAX_SHOWN);
  const extra = ids.length - shown.length;

  return (
    <Group gap="xs">
      {shown.map((id) => (
        <Badge
          key={id}
          component={Link}
          to={`${ROUTE_PATHS.INSTANCES}/${id}`}
          size="md"
          variant="default"
          style={{ textTransform: 'initial', cursor: 'pointer' }}
        >
          <Text size="xs">{id}</Text>
        </Badge>
      ))}
      {extra > 0 && (
        <Badge size="md" variant="default">
          <Text size="xs" c="dimmed">
            +{extra}
          </Text>
        </Badge>
      )}
    </Group>
  );
};
