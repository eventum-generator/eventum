import type { Extension } from '@codemirror/state';
import { vscodeDarkInit, vscodeLight } from '@uiw/codemirror-theme-vscode';

// VSCode Dark+ syntax on the Studio's own background instead of its grey, so
// the editor matches the shiki code blocks (also VSCode Dark+). The raised
// surface-2 reads as a lifted code area; the light theme is left as-is.
const evVscodeDark = vscodeDarkInit({
  settings: {
    background: 'var(--ev-surface-2)',
    gutterBackground: 'var(--ev-surface-2)',
  },
});

export function cmTheme(colorScheme: string): Extension {
  return colorScheme === 'dark' ? evVscodeDark : vscodeLight;
}
