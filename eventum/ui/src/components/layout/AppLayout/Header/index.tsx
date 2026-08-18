import { ActionIcon, Anchor, Box, Group, Image, Title } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconMenu2 } from '@tabler/icons-react';
import { FC } from 'react';
import { Link } from 'react-router-dom';

import { AboutModal } from './AboutModal';
import { UserMenu } from './UserMenu';
import { AppBreadcrumbs } from '@/components/layout/AppLayout/Header/AppBreadcrumbs';
import ThemeToggle from '@/components/ui/ThemeToggle';
import { ROUTE_PATHS } from '@/routing/paths';

interface HeaderProps {
  username: string;
  onSignOut: () => void;
  onMenuClick: () => void;
  onMobileMenuClick: () => void;
}

export const Header: FC<HeaderProps> = ({
  username,
  onSignOut,
  onMenuClick,
  onMobileMenuClick,
}) => {
  return (
    // The header is a fixed 60px band, so nothing here may wrap - a second
    // line is drawn over the page below it. Everything that cannot be made
    // to fit gives way instead: the breadcrumbs and the wordmark drop out at
    // the widths where they no longer earn their space.
    <Group
      justify="space-between"
      wrap="nowrap"
      h="100%"
      ml="xs"
      mr={{ base: 'xs', sm: 'xl' }}
    >
      <Group gap="lg" wrap="nowrap" style={{ minWidth: 0 }}>
        {/* One burger per navbar mode: the desktop column and the mobile
            overlay hold separate state, and CSS - not a media query read in
            JS - decides which of the two is live. */}
        <ActionIcon
          variant="transparent"
          onClick={onMenuClick}
          visibleFrom="sm"
        >
          <IconMenu2 size={20} />
        </ActionIcon>
        <ActionIcon
          variant="transparent"
          onClick={onMobileMenuClick}
          hiddenFrom="sm"
        >
          <IconMenu2 size={20} />
        </ActionIcon>
        <Anchor
          component={Link}
          to={ROUTE_PATHS.ROOT}
          underline="never"
          c="inherit"
          mr="md"
        >
          <Group gap="xs" wrap="nowrap">
            <Box>
              <Image
                src="/logo.svg"
                alt="Eventum Logo"
                h={27}
                w="auto"
                fit="contain"
                mx="auto"
                draggable={false}
              />
            </Box>
            <Box visibleFrom="xs">
              <Title fz="lg" fw="normal" style={{ whiteSpace: 'nowrap' }}>
                Eventum Studio
              </Title>
            </Box>
          </Group>
        </Anchor>
        <Box visibleFrom="sm" style={{ minWidth: 0 }}>
          <AppBreadcrumbs />
        </Box>
      </Group>
      <Group wrap="nowrap">
        <ThemeToggle />
        <Box ml={{ base: 0, sm: 'sm' }}>
          <UserMenu
            username={username}
            onSignOut={onSignOut}
            onOpenAboutModal={() => {
              modals.open({
                title: 'About Eventum',
                children: <AboutModal />,
                size: 540,
                padding: 'xl',
              });
            }}
          />
        </Box>
      </Group>
    </Group>
  );
};
