import { Box, Divider, NavLink, Stack } from '@mantine/core';
import { IconHome } from '@tabler/icons-react';
import { FC } from 'react';
import { Link, useLocation } from 'react-router-dom';

import {
  BOTTOM_NAVIGATION_DATA,
  NAVIGATION_DATA,
  TOP_NAVIGATION_DATA,
} from './data';
import { ROUTE_PATHS } from '@/routing/paths';

interface NavbarProps {
  /** Called after a navigation link is followed. On narrow viewports the
   *  navbar covers the whole page, so it has to close itself once the
   *  destination is chosen. */
  onNavigate?: () => void;
}

export const Navbar: FC<NavbarProps> = ({ onNavigate }) => {
  const { pathname } = useLocation();

  return (
    <Stack gap="0" h="100%" justify="space-between">
      <Box>
        <NavLink
          label="Home"
          leftSection={<IconHome size="19px" />}
          active={pathname === ROUTE_PATHS.ROOT}
          component={Link}
          to={ROUTE_PATHS.ROOT}
          onClick={onNavigate}
        />
        {TOP_NAVIGATION_DATA.map((item) => (
          <NavLink
            label={item.label}
            key={item.label}
            leftSection={<item.icon size="19px" />}
            active={pathname.startsWith(item.pathname)}
            component={Link}
            to={item.pathname}
            onClick={onNavigate}
          />
        ))}
        {NAVIGATION_DATA.map((group) => (
          <Box key={group.groupName}>
            <Divider />
            <NavLink label={group.groupName} defaultOpened>
              {group.items.map((item) => (
                <NavLink
                  label={item.label}
                  key={item.label}
                  leftSection={<item.icon size="19px" />}
                  active={pathname.startsWith(item.pathname)}
                  component={Link}
                  to={item.pathname}
                  onClick={onNavigate}
                />
              ))}
            </NavLink>
          </Box>
        ))}
      </Box>
      <Box>
        {BOTTOM_NAVIGATION_DATA.map((item) => (
          <NavLink
            label={item.label}
            key={item.label}
            leftSection={<item.icon size="19px" />}
            href={item.link}
            target="_blank"
          />
        ))}
      </Box>
    </Stack>
  );
};
