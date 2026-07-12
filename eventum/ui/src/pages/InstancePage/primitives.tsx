import { Box, Group, Paper, Stack, Text } from '@mantine/core';
import { FC, ReactNode } from 'react';

/** Uppercase muted section heading, matching the Home/Monitoring grammar. */
export const SectionLabel: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
    {children}
  </Text>
);

/** Faint inline separator dot for meta lines. */
export const Dot: FC = () => (
  <Box
    aria-hidden
    style={{
      width: 3,
      height: 3,
      borderRadius: '50%',
      background: 'var(--ev-faint)',
      flexShrink: 0,
    }}
  />
);

interface StatTileProps {
  label: string;
  value: string;
  unit?: string;
  color?: string;
}

/** A single live-metric readout tile: label over a bold monospace value. */
export const StatTile: FC<StatTileProps> = ({ label, value, unit, color }) => (
  <Paper withBorder radius="md" p="md">
    <Text size="xs" tt="uppercase" lts="0.5px" fw={600} c="dimmed">
      {label}
    </Text>
    <Group align="baseline" gap={6} wrap="nowrap" mt={6}>
      <Text
        fw={700}
        ff="monospace"
        style={{
          fontSize: '1.6rem',
          lineHeight: 1.1,
          fontVariantNumeric: 'tabular-nums',
          color,
        }}
      >
        {value}
      </Text>
      {unit ? (
        <Text size="sm" c="dimmed">
          {unit}
        </Text>
      ) : null}
    </Group>
  </Paper>
);

interface FieldProps {
  label: string;
  children: ReactNode;
}

/** A label/value row for the wiring definition list. */
export const Field: FC<FieldProps> = ({ label, children }) => (
  <Group justify="space-between" gap="md" wrap="nowrap" align="center">
    <Text size="sm" c="dimmed" style={{ flexShrink: 0 }}>
      {label}
    </Text>
    <Box style={{ minWidth: 0, textAlign: 'right' }}>{children}</Box>
  </Group>
);

/** A titled card with a section label above a bordered panel. */
export const Section: FC<{ label: string; children: ReactNode }> = ({
  label,
  children,
}) => (
  <Stack gap="xs">
    <SectionLabel>{label}</SectionLabel>
    <Paper withBorder radius="md" p="lg">
      {children}
    </Paper>
  </Stack>
);
