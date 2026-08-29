import { Box, Divider, Group, Paper, Stack, Text } from '@mantine/core';
import { FC, ReactNode, useEffect, useState } from 'react';

import { formatUptime } from './format';

/** Uppercase muted section heading, matching the app-wide grammar. */
export const SectionLabel: FC<{ color?: string; children: ReactNode }> = ({
  color,
  children,
}) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c={color ?? 'dimmed'}>
    {children}
  </Text>
);

/** A titled card: an icon + heading strip above a divider and the body. */
export const InfoCard: FC<{
  icon: ReactNode;
  title: string;
  children: ReactNode;
}> = ({ icon, title, children }) => (
  <Paper withBorder p="lg" h="100%">
    <Stack gap="sm" h="100%">
      <Group gap="sm" wrap="nowrap" align="center">
        <Box c="dimmed" style={{ display: 'flex' }}>
          {icon}
        </Box>
        <Text fw={600} fz="0.95rem">
          {title}
        </Text>
      </Group>
      <Divider />
      <Stack gap="sm" style={{ flex: 1 }}>
        {children}
      </Stack>
    </Stack>
  </Paper>
);

/** A definition row: label on the left, value on the right. */
export const Attr: FC<{ label: string; children: ReactNode }> = ({
  label,
  children,
}) => (
  <Group justify="space-between" wrap="nowrap" gap="md" align="baseline">
    <Text size="sm" c="dimmed" style={{ flexShrink: 0 }}>
      {label}
    </Text>
    <Box style={{ minWidth: 0, textAlign: 'right' }}>{children}</Box>
  </Group>
);

/** The mono, tabular value style used for every identity value. `color`
 *  is for the values that carry a state rather than a fact; left unset,
 *  the value reads in the default text color like every other one. */
export const AttrValue: FC<{
  title?: string;
  color?: string;
  children: ReactNode;
}> = ({ title, color, children }) => (
  <Text
    size="sm"
    fw={500}
    ff="monospace"
    title={title}
    truncate
    style={{ fontVariantNumeric: 'tabular-nums', color }}
  >
    {children}
  </Text>
);

/** A thin proportion bar for a snapshot percentage. */
export const Meter: FC<{ pct: number; color: string }> = ({ pct, color }) => (
  <Box
    style={{
      height: 4,
      borderRadius: 999,
      background: 'var(--mantine-color-default-border)',
      overflow: 'hidden',
    }}
  >
    <Box
      style={{
        height: '100%',
        width: `${Math.min(100, Math.max(0, pct))}%`,
        background: color,
        borderRadius: 999,
      }}
    />
  </Box>
);

/**
 * Uptime that advances on its own one-second timer, decoupled from data
 * polling, so it counts up smoothly instead of jumping on each refetch.
 * `sinceEpochSeconds` is a fixed epoch in seconds (e.g. host boot time).
 */
export const LiveUptime: FC<{ sinceEpochSeconds: number }> = ({
  sinceEpochSeconds,
}) => {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return <>{formatUptime(now / 1000 - sinceEpochSeconds)}</>;
};
