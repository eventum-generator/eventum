import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RenderOptions, RenderResult, render } from '@testing-library/react';
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
