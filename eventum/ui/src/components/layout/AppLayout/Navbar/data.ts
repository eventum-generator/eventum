import {
  IconActivity,
  IconBook,
  IconBug,
  IconFolder,
  IconLock,
  IconTransform,
  IconPlayerPlay,
  IconServerCog,
  IconSettings,
  IconUsersGroup,
} from '@tabler/icons-react';

import { LINKS } from '@/routing/links';
import { ROUTE_PATHS } from '@/routing/paths';

export const TOP_NAVIGATION_DATA = [
  {
    label: 'Monitoring',
    icon: IconActivity,
    pathname: ROUTE_PATHS.MONITORING,
  },
];

export const NAVIGATION_DATA = [
  {
    groupName: 'Generators',
    items: [
      {
        label: 'Projects',
        icon: IconFolder,
        pathname: ROUTE_PATHS.PROJECTS,
      },
      {
        label: 'Instances',
        icon: IconPlayerPlay,
        pathname: ROUTE_PATHS.INSTANCES,
      },
      {
        label: 'Scenarios',
        icon: IconTransform,
        pathname: ROUTE_PATHS.SCENARIOS,
      },
    ],
  },
  {
    groupName: 'Management',
    items: [
      {
        label: 'Secrets',
        icon: IconLock,
        pathname: ROUTE_PATHS.SECRETS,
      },
      {
        label: 'Settings',
        icon: IconSettings,
        pathname: ROUTE_PATHS.SETTINGS,
      },
      {
        label: 'Management',
        icon: IconServerCog,
        pathname: ROUTE_PATHS.MANAGEMENT,
      },
    ],
  },
];

export const BOTTOM_NAVIGATION_DATA = [
  {
    label: 'Documentation',
    icon: IconBook,
    link: LINKS.DOCUMENTATION,
  },
  {
    label: 'Join the community',
    icon: IconUsersGroup,
    link: LINKS.GITHUB_DISCUSSIONS,
  },
  {
    label: 'Report an issue',
    icon: IconBug,
    link: LINKS.GITHUB_ISSUES,
  },
];
