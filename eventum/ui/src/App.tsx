// sort-imports-ignore
import {
  CodeHighlight,
  CodeHighlightAdapterProvider,
  createShikiAdapter,
} from '@mantine/code-highlight';
import {
  MantineThemeProvider,
  MantineProvider,
  MantineThemeOverride,
  useMantineColorScheme,
} from '@mantine/core';
import { ContextMenuProvider } from 'mantine-contextmenu';

import { ModalsProvider } from '@mantine/modals';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RouterProvider } from 'react-router-dom';

import { theme } from '@/theme';
import { router } from '@/routing';
import { useMemo } from 'react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

async function loadShiki() {
  const { createHighlighter } = await import('shiki');
  const shiki = await createHighlighter({
    langs: [
      'csv',
      'jinja',
      'json',
      'log',
      'markdown',
      'toml',
      'tsv',
      'xml',
      'yaml',
    ],
    themes: ['dark-plus', 'light-plus'],
  });

  return shiki;
}
const shikiAdapter = createShikiAdapter(loadShiki);

function InnerApp() {
  const { colorScheme } = useMantineColorScheme();

  const innerTheme = useMemo(
    () =>
      ({
        components: {
          CodeHighlight: CodeHighlight.extend({
            defaultProps: {
              codeColorScheme:
                colorScheme === 'dark' ? 'dark-plus' : 'light-plus',
            },
          }),
        },
      }) as MantineThemeOverride,
    [colorScheme]
  );

  return (
    <MantineThemeProvider theme={innerTheme}>
      <RouterProvider router={router} />
    </MantineThemeProvider>
  );
}
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <CodeHighlightAdapterProvider adapter={shikiAdapter}>
          <Notifications />
          <ModalsProvider>
            <ContextMenuProvider>
              <InnerApp />
            </ContextMenuProvider>
          </ModalsProvider>
        </CodeHighlightAdapterProvider>
      </MantineProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
