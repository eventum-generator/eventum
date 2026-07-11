import { Box, Divider, NavLink, Stack } from '@mantine/core';
import { IconHome } from '@tabler/icons-react';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import {
  BOTTOM_NAVIGATION_DATA,
  NAVIGATION_DATA,
  TOP_NAVIGATION_DATA,
} from './data';
import { ROUTE_PATHS } from '@/routing/paths';

export const Navbar: FC = () => {
  return (
    <Stack gap="0" h="100%" justify="space-between">
      <Box>
        <NavLink
          label="Home"
          leftSection={<IconHome size="19px" />}
          active={location.pathname === ROUTE_PATHS.ROOT}
          component={Link}
          to={ROUTE_PATHS.ROOT}
        />
        {TOP_NAVIGATION_DATA.map((item) => (
          <NavLink
            label={item.label}
            key={item.label}
            leftSection={<item.icon size="19px" />}
            active={location.pathname.startsWith(item.pathname)}
            component={Link}
            to={item.pathname}
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
                  active={location.pathname.startsWith(item.pathname)}
                  component={Link}
                  to={item.pathname}
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
