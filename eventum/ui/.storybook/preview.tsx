import { MantineProvider } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { Notifications } from '@mantine/notifications';
import type { Preview } from '@storybook/react-vite';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContextMenuProvider } from 'mantine-contextmenu';
import { useEffect } from 'react';

import { theme } from '../src/theme';

// Docs-only pages (Foundations/*) render without the story decorators below,
// so nothing would set the colour scheme and every --ev-* token would resolve
// to nothing. Seed the toolbar's default scheme at preview load; the decorator
// still overrides it per-story whenever the Light/Dark control changes.
document.documentElement.dataset.mantineColorScheme = 'dark';

/** Only the two forced schemes the toolbar offers - never 'auto', which
 *  `MantineProvider.forceColorScheme` does not accept. */
type ForcedColorScheme = 'light' | 'dark';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function ApplyColorScheme({ scheme }: { scheme: ForcedColorScheme }) {
  useEffect(() => {
    document.documentElement.dataset.mantineColorScheme = scheme;
  }, [scheme]);

  return null;
}

const preview: Preview = {
  globalTypes: {
    colorScheme: {
      description: 'Color scheme',
      defaultValue: 'dark',
      toolbar: {
        icon: 'circlehollow',
        items: [
          { value: 'light', title: 'Light' },
          { value: 'dark', title: 'Dark' },
        ],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const scheme: ForcedColorScheme =
        context.globals.colorScheme === 'light' ? 'light' : 'dark';

      return (
        <QueryClientProvider client={queryClient}>
          <MantineProvider theme={theme} forceColorScheme={scheme}>
            <ApplyColorScheme scheme={scheme} />
            <Notifications />
            <ModalsProvider>
              <ContextMenuProvider>
                {/* Every story sits on the real app canvas so components read
                    in the active scheme, not on Storybook's white docs paper. */}
                <div
                  style={{
                    background: 'var(--ev-bg)',
                    padding: 'var(--ev-space-6)',
                  }}
                >
                  <Story />
                </div>
              </ContextMenuProvider>
            </ModalsProvider>
          </MantineProvider>
        </QueryClientProvider>
      );
    },
  ],
  parameters: {
    layout: 'padded',
  },
};

export default preview;
