import { Paper, Stack, Text } from '@mantine/core';
import { FC, ReactNode, useEffect, useState } from 'react';

import { formatUptime } from './format';

/** Uppercase muted section heading, matching the Home/Monitoring grammar. */
export const SectionLabel: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
    {children}
  </Text>
);

/** A titled card: a section label above a bordered panel. */
export const Section: FC<{ label: string; children: ReactNode }> = ({
  label,
  children,
}) => (
  <Stack gap="xs">
    <SectionLabel>{label}</SectionLabel>
    <Paper withBorder p="md">
      {children}
    </Paper>
  </Stack>
);

/**
 * Uptime that advances on its own one-second timer, decoupled from data
 * polling, so it counts up smoothly instead of jumping on each refetch.
 */
export const LiveUptime: FC<{ startTime: number }> = ({ startTime }) => {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return <>{formatUptime((now - startTime) / 1000)}</>;
};
