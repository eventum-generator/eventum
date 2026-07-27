// sort-imports-ignore
import '@mantine/core/styles.css';
import '@mantine/code-highlight/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/charts/styles.css';
import 'mantine-contextmenu/styles.layer.css';
import '@fontsource-variable/inter';
import '@/index.css';
import '@/theme/components.css';

import {
  ActionIcon,
  Checkbox,
  Combobox,
  Menu,
  Modal,
  NavLink,
  Paper,
  PasswordInput,
  Popover,
  Table,
  createTheme,
  defaultVariantColorsResolver,
  type CSSVariablesResolver,
  type MantineColorsTuple,
  type VariantColorsResolverInput,
} from '@mantine/core';

/* eslint-disable no-restricted-syntax -- colour scales are the one place
   concrete values are allowed; everything else reads Mantine variables. */

// Every scale below is a regular Mantine 10-shade ramp: 0 is the lightest
// tint, 9 the darkest shade. `primaryShade` picks shade 6 in the light scheme
// and shade 5 in the dark one, which makes Mantine derive:
//   --mantine-color-<c>-filled  = shade 6 (light) / shade 5 (dark)
//   --mantine-color-<c>-text    = shade 6 (light) / shade 4 (dark)
//   --mantine-color-<c>-light   = the same hue at 10-15% opacity
// So shade 6 carries the light-scheme colour of a semantic role and shade 4
// the dark-scheme one; every derived variable follows from there and no
// component needs a per-scheme patch.

// Neutrals of the dark scheme. Mantine derives the whole dark chrome from
// this ramp, so the indices are load-bearing:
//   0 text | 2 dimmed | 3 placeholder | 4 borders | 5 hover
//   6 controls (inputs, dropdowns, cards) | 7 panels (body) | 9 page canvas
const darkColorTuple: MantineColorsTuple = [
  '#ececf1',
  '#c9c9d4',
  '#9a9aa7',
  '#6f6f7d',
  '#2c2c36',
  '#202028',
  '#1c1c23',
  '#141419',
  '#101016',
  '#0b0b0e',
];

// Neutrals of the light scheme, same roles in reverse:
//   0 page canvas | 1 hover | 2 disabled | 3 panel borders
//   4 control borders | 5 placeholder | 6 dimmed | 9 text
const grayColorTuple: MantineColorsTuple = [
  '#f6f6f9',
  '#eeeef3',
  '#e6e6ee',
  '#dedee6',
  '#d4d4de',
  '#9b9bab',
  '#5c5c6b',
  '#45454f',
  '#2b2b33',
  '#16161c',
];

// Brand purple: #4d4de7 leads the light scheme, #7c7bf5 the dark one.
const primaryColorTuple: MantineColorsTuple = [
  '#f0f0ff',
  '#e0e0fb',
  '#c2c2f8',
  '#9d9cf6',
  '#7c7bf5',
  '#6262f0',
  '#4d4de7',
  '#3f3fcb',
  '#3434a8',
  '#292985',
];

// Danger.
const redColorTuple: MantineColorsTuple = [
  '#fdecec',
  '#fbd5d3',
  '#f8aca8',
  '#fa7d76',
  '#f85149',
  '#e63a37',
  '#cf222e',
  '#ad1b26',
  '#8c151f',
  '#6b1017',
];

// Success / running.
const greenColorTuple: MantineColorsTuple = [
  '#eafaee',
  '#cdf2d6',
  '#9be3ad',
  '#66d17f',
  '#3fb950',
  '#2a9c3d',
  '#1a7f37',
  '#14682c',
  '#0f5222',
  '#0a3b18',
];

// Warning. The light end leans amber-orange rather than olive: a dark yellow
// reads as muddy brown on a white surface, especially on a solid icon.
const yellowColorTuple: MantineColorsTuple = [
  '#fdf6e3',
  '#fbe9b8',
  '#f6d47a',
  '#e5b53f',
  '#d29922',
  '#d17d0e',
  '#b8650a',
  '#96500a',
  '#743c07',
  '#522905',
];

// Information.
const blueColorTuple: MantineColorsTuple = [
  '#e7f2ff',
  '#cae0ff',
  '#9dc6ff',
  '#6fadff',
  '#4d9fff',
  '#2b84ea',
  '#1971c2',
  '#135b9d',
  '#0e4677',
  '#093152',
];

// Inbound channel of the monitoring charts, and the second stop of the brand
// gradient.
const cyanColorTuple: MantineColorsTuple = [
  '#e6f7f7',
  '#c4ecec',
  '#97dcdd',
  '#7ed4d5',
  '#69ced0',
  '#2fadaf',
  '#0e8a8d',
  '#0b7073',
  '#08585a',
  '#063f41',
];

// Mantine reads these as the light scheme's panel colour and text colour.
const white = '#ffffff';
const black = '#16161c';

const shadows = {
  light:
    '0 1px 2px rgba(12, 12, 30, 0.04), 0 8px 24px -16px rgba(12, 12, 30, 0.18)',
  dark: '0 1px 2px rgba(0, 0, 0, 0.4), 0 12px 32px -16px rgba(0, 0, 0, 0.6)',
};

/* eslint-enable no-restricted-syntax */

const SEMANTIC_COLORS = ['green', 'yellow', 'red', 'blue'];

const softLightTints = Object.fromEntries(
  SEMANTIC_COLORS.flatMap((color) => [
    [
      `--mantine-color-${color}-light`,
      `color-mix(in srgb, var(--mantine-color-${color}-6) 16%, transparent)`,
    ],
    [
      `--mantine-color-${color}-light-hover`,
      `color-mix(in srgb, var(--mantine-color-${color}-6) 22%, transparent)`,
    ],
  ])
);

// The few variables Mantine either leaves too dark for our canvas or points
// at a shade that does not exist in a 5/6 primary shade setup.
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {
    // Menu items hover like table rows and combobox options.
    '--menu-item-hover': 'var(--mantine-color-default-hover)',
  },
  light: {
    // The page canvas behind the panels. Mantine has no variable for it:
    // --mantine-color-body is the panel colour, which panels, the app shell
    // and modals all read.
    '--ev-canvas': 'var(--mantine-color-gray-0)',
    // Shade 0 is the page canvas, so hover has to be one step further.
    '--mantine-color-default-hover': 'var(--mantine-color-gray-1)',
    // Mantine tints soft semantic surfaces at 10% in the light scheme, which
    // washes a status chip out to near-white. A denser tint lets the hue read
    // while the label keeps its contrast. The dark scheme already sits at 15%.
    ...softLightTints,
    '--mantine-shadow-sm': shadows.light,
  },
  dark: {
    '--ev-canvas': 'var(--mantine-color-dark-9)',
    // Mantine points these at shade 8, which is nearly black on our canvas.
    '--mantine-color-error': 'var(--mantine-color-red-4)',
    '--mantine-color-primary-light-color': 'var(--mantine-color-primary-4)',
    '--mantine-color-red-light-color': 'var(--mantine-color-red-4)',
    '--mantine-color-green-light-color': 'var(--mantine-color-green-4)',
    '--mantine-color-yellow-light-color': 'var(--mantine-color-yellow-4)',
    '--mantine-color-blue-light-color': 'var(--mantine-color-blue-4)',
    // Neutral chips stay muted rather than jumping to a near-white label.
    '--mantine-color-gray-light-color': 'var(--mantine-color-dark-2)',
    '--mantine-shadow-sm': shadows.dark,
  },
});

// Danger comes in three levels: filled (a decisive confirm), medium and
// ghost. Mantine covers the outer two, but its `default` variant ignores
// `color`, which would flatten the medium level into a plain neutral button.
// Keep that variant's neutral surface and give it back its red label.
function variantColorResolver(input: VariantColorsResolverInput) {
  const base = defaultVariantColorsResolver(input);

  if (input.variant === 'default' && input.color === 'red') {
    return {
      ...base,
      color: 'var(--mantine-color-red-text)',
      hover: 'var(--mantine-color-red-light)',
      hoverColor: 'var(--mantine-color-red-text)',
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
  // Two tiers: controls at md, surfaces (panels, modals) at lg.
  radius: {
    xs: '4px',
    sm: '6px',
    md: '8px',
    lg: '12px',
    xl: '16px',
  },
  defaultRadius: 'md',
  cursorType: 'pointer',
  focusRing: 'auto',
  white,
  black,
  colors: {
    dark: darkColorTuple,
    gray: grayColorTuple,
    primary: primaryColorTuple,
    red: redColorTuple,
    green: greenColorTuple,
    yellow: yellowColorTuple,
    blue: blueColorTuple,
    cyan: cyanColorTuple,
  },
  primaryColor: 'primary',
  primaryShade: { light: 6, dark: 5 },
  variantColorResolver,
  defaultGradient: {
    from: 'var(--mantine-color-primary-4)',
    to: 'var(--mantine-color-cyan-4)',
    deg: 12,
  },
  components: {
    // Icon buttons are chrome: neutral by default, semantic only where a call
    // site asks for it (`color="red"` on a delete action).
    ActionIcon: ActionIcon.extend({ defaultProps: { color: 'gray' } }),
    // A checkbox is small enough that the control radius reads as a circle;
    // one step down keeps the corner crisp.
    Checkbox: Checkbox.extend({ defaultProps: { radius: 'xs' } }),
    Combobox: Combobox.extend({ defaultProps: { shadow: 'sm' } }),
    Menu: Menu.extend({ defaultProps: { shadow: 'sm' } }),
    // House rule: every modal is vertically centered (Mantine defaults to top).
    Modal: Modal.extend({ defaultProps: { centered: true, radius: 'lg' } }),
    // An active item is marked by the accent rail and tint; keeping the label
    // in the text colour holds the sidebar readable.
    NavLink: NavLink.extend({
      vars: () => ({
        root: { '--nl-color': 'var(--mantine-color-text)' },
        children: {},
      }),
    }),
    Paper: Paper.extend({ defaultProps: { radius: 'lg', shadow: 'sm' } }),
    // PasswordInput defaults to md (16px) while every other input defaults to
    // sm (14px); pin it to sm so it matches sibling TextInputs everywhere.
    PasswordInput: PasswordInput.extend({ defaultProps: { size: 'sm' } }),
    Popover: Popover.extend({ defaultProps: { shadow: 'sm' } }),
    Table: Table.extend({
      defaultProps: {
        highlightOnHover: true,
        verticalSpacing: 'sm',
        horizontalSpacing: 'md',
      },
    }),
  },
});
