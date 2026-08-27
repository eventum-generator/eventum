import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  RenderHookOptions,
  RenderHookResult,
  RenderOptions,
  RenderResult,
  render,
  renderHook,
} from '@testing-library/react';
import { FC, ReactElement, ReactNode } from 'react';

import { cssVariablesResolver, theme } from '@/theme';

/**
 * Render a component under the providers the app mounts it in: the studio
 * theme and a query client of its own, so no cached response leaks from one
 * test into the next.
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const Providers: FC<{ children: ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <MantineProvider
        theme={theme}
        cssVariablesResolver={cssVariablesResolver}
        defaultColorScheme="dark"
      >
        {children}
      </MantineProvider>
    </QueryClientProvider>
  );

  return render(ui, { wrapper: Providers, ...options });
}

/**
 * Render a hook under a query client of its own, and hand the client
 * back.
 *
 * The client is what the assertions are usually about: a mutation is
 * correct when the queries it should have invalidated are the ones that
 * refetch, and that is only visible from the client.
 */
export function renderHookWithClient<Result, Props>(
  hook: (props: Props) => Result,
  options?: Omit<RenderHookOptions<Props>, 'wrapper'>
): RenderHookResult<Result, Props> & { queryClient: QueryClient } {
  const queryClient = new QueryClient({
    defaultOptions: {
      // A cache entry seeded without an observer would otherwise be
      // collected before the assertion reads it back.
      queries: { retry: false, gcTime: Number.POSITIVE_INFINITY },
      mutations: { retry: false },
    },
  });

  const Providers: FC<{ children: ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  return {
    ...renderHook(hook, { wrapper: Providers, ...options }),
    queryClient,
  };
}
