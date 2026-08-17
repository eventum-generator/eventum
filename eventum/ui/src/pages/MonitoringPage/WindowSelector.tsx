import { Group, SegmentedControl, Text } from '@mantine/core';
import { FC } from 'react';

import { WINDOW_OPTIONS } from './history';

interface WindowSelectorProps {
  points: number;
  onChange: (points: number) => void;
}

/**
 * Length of the window every chart on the page draws. History is collected in
 * the browser from the moment the page opens, so a longer window starts out
 * partly empty and fills in as the polls arrive.
 */
export const WindowSelector: FC<WindowSelectorProps> = ({
  points,
  onChange,
}) => (
  <Group gap="xs" wrap="nowrap">
    <Text size="xs" c="dimmed">
      Window
    </Text>
    <SegmentedControl
      size="xs"
      value={String(points)}
      onChange={(value) => onChange(Number(value))}
      data={WINDOW_OPTIONS}
    />
  </Group>
);
