import {
  Button,
  type ButtonProps,
  Group,
  Menu,
  Stack,
  Text,
} from '@mantine/core';
import type { Meta, StoryObj } from '@storybook/react-vite';
import {
  IconChevronDown,
  IconDownload,
  IconPlayerStop,
  IconPlus,
  IconReload,
  IconTrash,
} from '@tabler/icons-react';

/**
 * How Eventum uses Button. The catalog is prescriptive: it works out every
 * scenario the product needs - the neutral emphasis ladder (primary /
 * secondary / tertiary), the destructive danger tone as its own ladder, and
 * one shared states grid - not just what happens to be wired up today, and not
 * the whole Mantine surface.
 */
const meta = {
  title: 'Components/Button',
  component: Button,
  argTypes: {
    variant: {
      control: 'inline-radio',
      options: ['filled', 'default', 'subtle'],
      description:
        '`filled` = primary, `default` = secondary, `subtle` = tertiary.',
      table: { defaultValue: { summary: 'filled' } },
    },
    size: {
      control: 'inline-radio',
      options: ['xs', 'sm', 'md'],
      description:
        '`xs` dense (toolbars, table rows), `sm` default, `md` prominent CTA.',
      table: { defaultValue: { summary: 'sm' } },
    },
    color: {
      control: 'inline-radio',
      options: ['primary', 'red'],
      description: 'Tone: `primary` (neutral) or `red` (danger / destructive).',
      table: { defaultValue: { summary: 'primary' } },
    },
    disabled: {
      control: 'boolean',
      description: 'Non-interactive; used when a precondition is not met.',
    },
    loading: {
      control: 'boolean',
      description: 'Spinner + blocks re-entry while a backend action runs.',
    },
    children: { control: 'text', description: 'Label - always a verb.' },
  },
  args: {
    children: 'Save changes',
    variant: 'filled',
    size: 'sm',
    color: 'primary',
    disabled: false,
    loading: false,
  },
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

const noControls = { controls: { disable: true } };

// --- Playground ------------------------------------------------------------

/** Live sandbox - drive the props we use from the Controls panel. */
export const Playground: Story = {};

// --- Overviews (rest only) -------------------------------------------------

/** The neutral emphasis ladder, at rest. One primary per view; secondary and
 *  tertiary carry the supporting actions. */
export const Roles: Story = {
  parameters: noControls,
  render: () => (
    <Group>
      <Button>Save changes</Button>
      <Button variant="default">Cancel</Button>
      <Button variant="subtle">Skip for now</Button>
    </Group>
  ),
};

/** The destructive tone, at rest, on its own three-level ladder - so the loud
 *  filled red stays rare (the decisive confirm). Medium is flat with a
 *  red-tinted fill; subtle is for rows and menus. */
export const Danger: Story = {
  parameters: noControls,
  render: () => (
    <Group>
      <Button color="red" leftSection={<IconTrash size={16} />}>
        Delete instance
      </Button>
      <Button color="red" variant="default">
        Delete
      </Button>
      <Button color="red" variant="subtle">
        Remove
      </Button>
    </Group>
  ),
};

// --- One shared states grid (all roles, incl. danger) ----------------------

interface StateRole {
  readonly name: string;
  readonly props: Partial<ButtonProps>;
}

const STATE_CELLS = [
  { label: 'Rest' },
  { label: 'Loading', loading: true },
  { label: 'Disabled', disabled: true },
];

const ALL_ROLES: StateRole[] = [
  { name: 'Primary', props: {} },
  { name: 'Secondary', props: { variant: 'default' } },
  { name: 'Tertiary', props: { variant: 'subtle' } },
  { name: 'Danger', props: { color: 'red' } },
  { name: 'Danger medium', props: { variant: 'default', color: 'red' } },
  { name: 'Danger subtle', props: { variant: 'subtle', color: 'red' } },
];

/** Every role - neutral and danger - across its states, in one grid. Hover
 *  darkens a step; focus shows the accent ring; loading keeps the colour +
 *  spinner (busy, not disabled); disabled is a muted surface. */
export const States: Story = {
  parameters: noControls,
  render: () => (
    <Stack gap="lg">
      {ALL_ROLES.map((role) => (
        <Group key={role.name} align="center" wrap="nowrap">
          <Text size="xs" c="dimmed" w={110}>
            {role.name}
          </Text>
          {STATE_CELLS.map((cell) => (
            <Button
              key={cell.label}
              {...role.props}
              loading={cell.loading}
              disabled={cell.disabled}
            >
              {cell.label}
            </Button>
          ))}
        </Group>
      ))}
    </Stack>
  ),
};

/** Three sizes cover the product's scenarios: `xs` for dense contexts
 *  (toolbars, table-row and inline actions), `sm` the default everywhere
 *  (forms, dialogs, most actions), `md` for a prominent standalone call to
 *  action (empty states, page hero). `lg` / `xl` are intentionally out of the
 *  system - Studio is a tool UI with no hero-marketing scenario for them. */
export const Sizes: Story = {
  parameters: noControls,
  render: () => (
    <Group align="center">
      <Button size="xs">Compact (xs)</Button>
      <Button size="sm">Default (sm)</Button>
      <Button size="md">Prominent (md)</Button>
    </Group>
  ),
};

// --- Compositions ----------------------------------------------------------

/** A leading icon reinforces the action; a trailing icon signals a result. */
export const WithIcons: Story = {
  parameters: noControls,
  render: () => (
    <Group>
      <Button leftSection={<IconPlus size={16} />}>New generator</Button>
      <Button variant="default" rightSection={<IconDownload size={16} />}>
        Export
      </Button>
      <Button
        color="red"
        variant="subtle"
        leftSection={<IconTrash size={16} />}
      >
        Delete
      </Button>
    </Group>
  ),
};

/** Dialog footers stack full-width, primary on top. A destructive confirm
 *  pairs the red action with a neutral Cancel. */
export const FullWidth: Story = {
  parameters: noControls,
  render: () => (
    <Stack maw={320}>
      <Button color="red" fullWidth>
        Delete instance
      </Button>
      <Button fullWidth variant="default">
        Cancel
      </Button>
    </Stack>
  ),
};

/** Grouped, attached actions that belong together (instance controls). */
export const ButtonGroup: Story = {
  parameters: noControls,
  render: () => (
    <Button.Group>
      <Button variant="default" leftSection={<IconReload size={16} />}>
        Restart
      </Button>
      <Button variant="default" leftSection={<IconPlayerStop size={16} />}>
        Stop
      </Button>
    </Button.Group>
  ),
};

/** Split button: a primary action plus a menu of related variants. */
export const SplitButton: Story = {
  parameters: noControls,
  render: () => (
    <Button.Group>
      <Button>Run</Button>
      <Menu position="bottom-end" withinPortal>
        <Menu.Target>
          <Button px="xs" aria-label="More run options">
            <IconChevronDown size={16} />
          </Button>
        </Menu.Target>
        <Menu.Dropdown>
          <Menu.Item>Run and download</Menu.Item>
          <Menu.Item>Run in background</Menu.Item>
        </Menu.Dropdown>
      </Menu>
    </Button.Group>
  ),
};

/** The one exception: the sign-in screen's brand button. Not a general
 *  variant - do not use gradient anywhere else. */
export const BrandSignIn: Story = {
  parameters: noControls,
  render: () => (
    <Stack gap="xs" maw={320}>
      <Button variant="gradient" fullWidth>
        Sign in
      </Button>
      <Text size="xs" c="dimmed">
        Sign-in only. Every other button uses filled / default / subtle.
      </Text>
    </Stack>
  ),
};
