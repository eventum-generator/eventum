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
}

export const Header: FC<HeaderProps> = ({
  username,
  onSignOut,
  onMenuClick,
}) => {
  return (
    <Group justify="space-between" h="100%" ml="xs" mr="xl">
      <Group gap="lg">
        <ActionIcon variant="transparent" onClick={onMenuClick}>
          <IconMenu2 size={20} />
        </ActionIcon>
        <Anchor
          component={Link}
          to={ROUTE_PATHS.ROOT}
          underline="never"
          c="inherit"
          mr="md"
        >
          <Group gap="xs">
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
            <Box>
              <Title fz="lg" fw="normal">
                Eventum Studio
              </Title>
            </Box>
          </Group>
        </Anchor>
        <AppBreadcrumbs />
      </Group>
      <Group>
        <ThemeToggle />
        <Box ml="sm">
          <UserMenu
            username={username}
            onSignOut={onSignOut}
            onOpenAboutModal={() => {
              modals.open({
                title: 'About Eventum',
                children: <AboutModal />,
              });
            }}
          />
        </Box>
      </Group>
    </Group>
  );
};
