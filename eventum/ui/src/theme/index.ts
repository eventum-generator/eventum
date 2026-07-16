// sort-imports-ignore
import '@mantine/core/styles.css';
import '@mantine/code-highlight/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/charts/styles.css';
import 'mantine-contextmenu/styles.layer.css';
import '@fontsource-variable/inter';
import '@/theme/tokens.css';
import '@/index.css';
import '@/theme/components.css';

import {
  Checkbox,
  Modal,
  createTheme,
  type MantineColorsTuple,
} from '@mantine/core';

const primaryColorTuple: MantineColorsTuple = [
  '#ececff', '#d4d5fd', '#a7a7f5', '#8282ef', '#4d4de7',
  '#3332e4', '#2525e3', '#1819ca', '#1015b6', '#0211a0',
];

export const theme = createTheme({
  autoContrast: true,
  fontFamily:
    "'Inter Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  fontFamilyMonospace:
    "ui-monospace, 'Cascadia Code', 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace",
  headings: {
    fontFamily:
      "'Inter Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    fontWeight: '650',
  },
  defaultRadius: 'md',
  cursorType: 'pointer',
  focusRing: 'auto',
  colors: { primary: primaryColorTuple },
  primaryColor: 'primary',
  primaryShade: 3,
  defaultGradient: { from: primaryColorTuple[3], to: 'var(--ev-cyan)', deg: 14 },
  components: {
    Checkbox: Checkbox.extend({ defaultProps: { radius: 'sm' } }),
    // House rule: every modal is vertically centered (Mantine defaults to top).
    Modal: Modal.extend({ defaultProps: { centered: true } }),
  },
});
