import { AppShell, Center, Loader } from '@mantine/core';
import { useDisclosure, useLocalStorage } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { Outlet, useNavigate } from 'react-router-dom';

import { Header } from './Header';
import { Navbar } from './Navbar';
import { useCurrentUser, useLogoutMutation } from '@/api/hooks/useAuth';
import { ROUTE_PATHS } from '@/routing/paths';

export default function AppLayout() {
  const navigate = useNavigate();
  const {
    data: user,
    isLoading: isUserLoading,
    isSuccess: isUserSuccess,
  } = useCurrentUser();
  const logout = useLogoutMutation();

  // Below the navbar breakpoint Mantine gives the navbar the full viewport
  // width, so "opened" there means an overlay over the page rather than a
  // column beside it. The two modes therefore need their own state: the
  // desktop column is a persisted preference, the mobile overlay starts
  // closed on every load and shuts itself on navigation.
  const [isNavbarOpened, setNavbarOpened] = useLocalStorage({
    key: 'navbar-opened',
    defaultValue: true,
  });
  const [isMobileNavbarOpened, mobileNavbar] = useDisclosure(false);

  if (isUserLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (!isUserSuccess) {
    void navigate(ROUTE_PATHS.SIGNIN);
    return;
  }

  return (
    <AppShell
      padding="md"
      header={{ height: 60 }}
      navbar={{
        width: 220,
        breakpoint: 'sm',
        collapsed: {
          desktop: !isNavbarOpened,
          mobile: !isMobileNavbarOpened,
        },
      }}
    >
      <AppShell.Header>
        <Header
          username={user}
          onSignOut={() =>
            logout.mutate(undefined, {
              onSuccess: () => void navigate(ROUTE_PATHS.SIGNIN),
              onError: (error) =>
                notifications.show({
                  title: 'Sign out failed',
                  message: error.message,
                  color: 'red',
                }),
            })
          }
          onMenuClick={() => setNavbarOpened((prev) => !prev)}
          onMobileMenuClick={mobileNavbar.toggle}
        />
      </AppShell.Header>

      <AppShell.Navbar>
        <Navbar onNavigate={mobileNavbar.close} />
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
