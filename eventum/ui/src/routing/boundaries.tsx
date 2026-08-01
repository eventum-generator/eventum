import { Center, Loader } from '@mantine/core';
import { Suspense } from 'react';
import { Outlet, useRouteError } from 'react-router-dom';

import ErrorPage from '@/pages/ErrorPage';

function RouteFallback() {
  return (
    <Center h="100vh" w="100vw">
      <Loader size="lg" />
    </Center>
  );
}

/**
 * Root layout route: keeps one app-wide Suspense boundary for the lazy pages.
 * A data router (createBrowserRouter) is what makes navigation blocking
 * (useBlocker) available, which the unsaved-changes guards rely on.
 */
export function RootBoundary() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Outlet />
    </Suspense>
  );
}

/** App-wide error element; resetting reloads the document. */
export function RouteError() {
  const error = useRouteError();
  return (
    <ErrorPage
      error={error instanceof Error ? error : undefined}
      resetError={() => globalThis.location.reload()}
    />
  );
}
