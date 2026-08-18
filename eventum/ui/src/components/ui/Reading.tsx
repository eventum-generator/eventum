import { Group, Text } from '@mantine/core';
import { Icon } from '@tabler/icons-react';
import { FC } from 'react';

interface ReadingProps {
  icon: Icon;
  value: string;
  label: string;
  /** Set only when the figure itself carries a warning. */
  color?: string;
}

/**
 * One live figure in a strip of them: a muted icon that says which reading it
 * is, the figure, and its caption. The figures share one colour on purpose -
 * an icon separates them without turning the strip into a palette, so a
 * colour anywhere in the strip means that figure needs attention.
 */
export const Reading: FC<ReadingProps> = ({
  icon: ReadingIcon,
  value,
  label,
  color,
}) => (
  <Group gap={7} wrap="nowrap" align="center">
    <ReadingIcon
      size={15}
      stroke={1.6}
      color={color ?? 'var(--mantine-color-dimmed)'}
    />
    <Text
      size="md"
      fw={700}
      ff="monospace"
      c={color}
      style={{ fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}
    >
      {value}
    </Text>
    <Text size="xs" c="dimmed">
      {label}
    </Text>
  </Group>
);
