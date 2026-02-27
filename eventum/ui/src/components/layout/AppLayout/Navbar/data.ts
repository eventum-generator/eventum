import {
  IconBook,
  IconBug,
  IconFolder,
  IconLock,
  IconPlayerPlay,
  IconServerCog,
  IconSettings,
  IconUsersGroup,
} from '@tabler/icons-react';

import { LINKS } from '@/routing/links';
import { ROUTE_PATHS } from '@/routing/paths';

export const NAVIGATION_DATA = [
  {
    groupName: 'Generators',
    items: [
      {
        label: 'Instances',
        icon: IconPlayerPlay,
        pathname: ROUTE_PATHS.INSTANCES,
      },
      {
        label: 'Projects',
        icon: IconFolder,
        pathname: ROUTE_PATHS.PROJECTS,
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
