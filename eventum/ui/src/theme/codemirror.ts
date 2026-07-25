import type { Extension } from '@codemirror/state';
import { vscodeDarkInit, vscodeLight } from '@uiw/codemirror-theme-vscode';

// VSCode Dark+ syntax on the Studio's own background instead of its grey, so
// the editor matches the shiki code blocks (also VSCode Dark+). The control
// surface reads as a lifted code area; the light theme is left as-is.
const evVscodeDark = vscodeDarkInit({
  settings: {
    background: 'var(--mantine-color-dark-6)',
    gutterBackground: 'var(--mantine-color-dark-6)',
  },
});

export function cmTheme(colorScheme: string): Extension {
  return colorScheme === 'dark' ? evVscodeDark : vscodeLight;
}
