import { Group, Text, Title } from '@mantine/core';
import { FC, ReactNode } from 'react';

interface SectionHeaderProps {
  /** Leading glyph, sized by the caller (18px matches the panel headers). */
  icon: ReactNode;
  title: string;
  /** Muted text shown next to the title (e.g. a count). */
  meta?: ReactNode;
  /** Right-aligned controls for the section. */
  children?: ReactNode;
}

/**
 * One header shape for every panel on the scenario page (Instances, Data
 * Flow, Global State) so the sections read as one system: a glyph, the
 * title, optional muted meta, and optional right-aligned actions.
 */
export const SectionHeader: FC<SectionHeaderProps> = ({
  icon,
  title,
  meta,
  children,
}) => (
  <Group justify="space-between" align="center" wrap="nowrap">
    <Group gap="sm" align="center" wrap="nowrap" style={{ minWidth: 0 }}>
      <Group gap="xs" align="center" wrap="nowrap">
        {icon}
        <Title order={5} fw={600}>
          {title}
        </Title>
      </Group>
      {meta !== undefined && (
        <Text size="xs" c="dimmed">
          {meta}
        </Text>
      )}
    </Group>
    {children}
  </Group>
);
