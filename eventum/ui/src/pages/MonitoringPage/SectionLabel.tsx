import { Text } from '@mantine/core';
import { FC, ReactNode } from 'react';

export const SectionLabel: FC<{ children: ReactNode }> = ({ children }) => (
  <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
    {children}
  </Text>
);
