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
  PasswordInput,
  createTheme,
  defaultVariantColorsResolver,
  type MantineColorsTuple,
  type VariantColorsResolverInput,
} from '@mantine/core';

/* eslint-disable no-restricted-syntax -- Mantine colour scales need 10 concrete shades, not tokens */
// Brand purple. primaryShade=3 picks index 3 (#8282ef) for the filled variant.
const primaryColorTuple: MantineColorsTuple = [
  '#ececff',
  '#d4d5fd',
  '#a7a7f5',
  '#8282ef',
  '#6f6ee9',
  '#3332e4',
  '#2525e3',
  '#1819ca',
  '#1015b6',
  '#0211a0',
];
// Danger scale. With primaryShade=3, index 3 is the colour a filled `color="red"`
// button uses - a solid, not-garish red (5.36:1 with a white label, calmer than
// a bright red on the dark canvas). Mantine's stock red is a pale pink there.
const redColorTuple: MantineColorsTuple = [
  '#fdeaec',
  '#f8ccd0',
  '#efa0a6',
  '#cf222e',
  '#bb1f29',
  '#a51b25',
  '#8f1720',
  '#78131b',
  '#620f16',
  '#4d0c12',
];
/* eslint-enable no-restricted-syntax */

// Buttons are almost entirely native Mantine: the two scales above + primaryShade
// drive filled (primary), default (secondary, restyled in components.css),
// color="red" (danger), and all states. The only tweak is the subtle (tertiary)
// variant: Mantine renders its text at shade 3 (#8282ef, too light to read as an
// action) and its hover as a same-hue tint (the coloured label vanishes on it).
// So subtle gets the deeper accent text (red stays red) and a NEUTRAL hover
// surface, keeping the label legible. Every other variant defers to Mantine.
function variantColorResolver(input: VariantColorsResolverInput) {
  const base = defaultVariantColorsResolver(input);
  // Secondary (default): flat, borderless. `color="red"` makes it the
  // medium-emphasis danger - a red-tinted fill (the same surface subtle danger
  // uses on hover) + red label; the neutral secondary stays a muted grey.
  if (input.variant === 'default') {
    const danger = input.color === 'red';
    return {
      ...base,
      background: danger
        ? 'var(--ev-danger-subtle-hover)'
        : 'var(--ev-secondary-bg)',
      hover: danger
        ? 'var(--ev-danger-secondary-hover)'
        : 'var(--ev-secondary-hover)',
      color: danger ? 'var(--ev-bad)' : 'var(--ev-text)',
      border: 'transparent',
    };
  }
  if (input.variant === 'subtle') {
    const danger = input.color === 'red';
    return {
      ...base,
      color: danger ? 'var(--ev-bad)' : 'var(--ev-accent)',
      // On hover a subtle button fills in. Danger gets a slight red-tinted fill
      // (keeps its red label); others fill to a neutral surface. The neutral
      // label colour is theme-aware (--ev-subtle-hover-fg): light keeps the
      // accent (a dark purple is crisp on the light fill), dark goes neutral (a
      // light purple would turn muddy on the dark fill).
      hover: danger
        ? 'var(--ev-danger-subtle-hover)'
        : 'var(--ev-subtle-hover)',
      hoverColor: danger ? 'var(--ev-bad)' : 'var(--ev-subtle-hover-fg)',
    };
  }
  return base;
}

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
  colors: { primary: primaryColorTuple, red: redColorTuple },
  primaryColor: 'primary',
  primaryShade: 3,
  variantColorResolver,
  defaultGradient: {
    from: 'var(--ev-grad-from)',
    to: 'var(--ev-grad-to)',
    deg: 14,
  },
  components: {
    Checkbox: Checkbox.extend({ defaultProps: { radius: 'sm' } }),
    // House rule: every modal is vertically centered (Mantine defaults to top).
    Modal: Modal.extend({ defaultProps: { centered: true } }),
    // PasswordInput defaults to md (16px) while every other input defaults to
    // sm (14px); pin it to sm so it matches sibling TextInputs everywhere.
    PasswordInput: PasswordInput.extend({ defaultProps: { size: 'sm' } }),
  },
});
