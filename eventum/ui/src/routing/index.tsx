import { Center, Loader } from '@mantine/core';
import { Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { useRoutes } from 'react-router-dom';

import { routes } from './config';
import ErrorPage from '@/pages/ErrorPage';

function RouteFallback() {
  return (
    <Center h="100vh" w="100vw">
      <Loader size="lg" />
    </Center>
  );
}

export default function AppRouter() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <ErrorBoundary
        FallbackComponent={({ error, resetErrorBoundary }) => (
          <ErrorPage
            error={error instanceof Error ? error : undefined}
            resetError={() => {
              resetErrorBoundary();
              globalThis.location.reload();
            }}
          />
        )}
      >
        {useRoutes(routes)}
      </ErrorBoundary>
    </Suspense>
  );
}
