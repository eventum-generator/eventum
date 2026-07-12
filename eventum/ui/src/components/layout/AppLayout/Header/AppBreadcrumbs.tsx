import { Badge, Breadcrumbs } from '@mantine/core';
import { IconChevronRight } from '@tabler/icons-react';
import { FC } from 'react';
import { Link, matchPath, useLocation } from 'react-router-dom';

import { ROUTE_PATHS } from '@/routing/paths';

// Route patterns a breadcrumb segment may link to. Excludes auth and
// the not-found page, which are not reachable destinations from a crumb.
const NAVIGABLE_PATTERNS = [
  ROUTE_PATHS.ROOT,
  ROUTE_PATHS.MONITORING,
  ROUTE_PATHS.INSTANCES,
  ROUTE_PATHS.INSTANCE,
  ROUTE_PATHS.PROJECTS,
  ROUTE_PATHS.PROJECT,
  ROUTE_PATHS.SCENARIOS,
  ROUTE_PATHS.SCENARIO,
  ROUTE_PATHS.SECRETS,
  ROUTE_PATHS.SETTINGS,
  ROUTE_PATHS.MANAGEMENT,
];

function isNavigable(path: string): boolean {
  return NAVIGABLE_PATTERNS.some((pattern) => matchPath(pattern, path));
}

export const AppBreadcrumbs: FC = () => {
  const location = useLocation();
  const segments = location.pathname.split('/').slice(1);

  return (
    <Breadcrumbs
      separator={<IconChevronRight size={'16px'} />}
      separatorMargin="0"
    >
      {segments.map((segment, index) => {
        const path = '/' + segments.slice(0, index + 1).join('/');
        const label = segment === '' ? 'Home' : decodeURIComponent(segment);
        const textTransform = index === 0 ? 'capitalize' : 'none';
        const isLast = index === segments.length - 1;

        // The current page (last crumb) and any segment that does not
        // resolve to a real route stay plain text - never a dead link.
        if (isLast || !isNavigable(path)) {
          return (
            <Badge
              key={path}
              variant="light"
              radius="sm"
              style={{ textTransform }}
            >
              {label}
            </Badge>
          );
        }

        return (
          <Badge
            key={path}
            component={Link}
            to={path}
            variant="light"
            radius="sm"
            style={{ textTransform, cursor: 'pointer', textDecoration: 'none' }}
          >
            {label}
          </Badge>
        );
      })}
    </Breadcrumbs>
  );
};
