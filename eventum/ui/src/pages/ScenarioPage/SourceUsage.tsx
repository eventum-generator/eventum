import {
  Collapse,
  Divider,
  Group,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconArrowRight,
  IconChevronDown,
  IconChevronRight,
  IconFile,
} from '@tabler/icons-react';
import { FC, useState } from 'react';

import { SourcePreview } from './SourcePreview';
import { SourceUsageEntry, WARNING_LABEL } from './source-usage';

interface KeyChipProps {
  label: string;
  /** Accent colour applied to the border on hover, by flow direction. */
  color: string;
  onEnter: () => void;
  onLeave: () => void;
}

/** A single global-state key touched by a template. Hovering it lights the
 *  matching edge on the data-flow diagram above. */
const KeyChip: FC<KeyChipProps> = ({ label, color, onEnter, onLeave }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <span
      onMouseEnter={() => {
        setHovered(true);
        onEnter();
      }}
      onMouseLeave={() => {
        setHovered(false);
        onLeave();
      }}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 22,
        padding: '0 8px',
        borderRadius: 'var(--mantine-radius-sm)',
        fontSize: 12,
        fontFamily: 'var(--mantine-font-family-monospace)',
        background: 'var(--mantine-color-gray-light)',
        color: 'var(--mantine-color-text)',
        border: `1px solid ${hovered ? color : 'var(--mantine-color-default-border)'}`,
        transition: 'border-color 120ms ease',
      }}
    >
      {label}
    </span>
  );
};

interface FlowRowProps {
  direction: 'write' | 'read';
  keys: string[];
  onEnterKey: (key: string) => void;
  onLeaveKey: () => void;
}

const FLOW = {
  write: {
    label: 'writes',
    color: 'var(--mantine-color-primary-text)',
    Icon: IconArrowRight,
  },
  read: {
    label: 'reads',
    color: 'var(--mantine-color-cyan-text)',
    Icon: IconArrowLeft,
  },
} as const;

/** One direction's keys: a fixed-width leader (arrow + label) so the write
 *  and read rows line up, followed by the key chips. */
const FlowRow: FC<FlowRowProps> = ({
  direction,
  keys,
  onEnterKey,
  onLeaveKey,
}) => {
  const { label, color, Icon } = FLOW[direction];
  return (
    <Group gap={6} wrap="wrap" align="center">
      <Group gap={4} wrap="nowrap" w={58} style={{ flexShrink: 0 }}>
        <Icon size={13} style={{ color, flexShrink: 0 }} />
        <Text size="xs" c="dimmed">
          {label}
        </Text>
      </Group>
      {keys.map((key) => (
        <KeyChip
          key={key}
          label={key}
          color={color}
          onEnter={() => onEnterKey(key)}
          onLeave={onLeaveKey}
        />
      ))}
    </Group>
  );
};

interface SourceUsageProps {
  generatorId: string;
  entries: SourceUsageEntry[];
  /** Highlight a specific read/write edge on the diagram. */
  onHighlightEdge?: (
    generatorId: string,
    keyName: string,
    direction?: 'write' | 'read'
  ) => void;
  /** Highlight a diagram node (used to keep the instance lit while scanning). */
  onHoverNode?: (nodeId: string | null) => void;
}

/**
 * The read/write flow of one instance, per file. Each template or script
 * shows the global-state keys it writes and reads as chips (hover -> the
 * matching edge lights up on the data-flow diagram) and expands inline to its
 * source.
 */
export const SourceUsage: FC<SourceUsageProps> = ({
  generatorId,
  entries,
  onHighlightEdge,
  onHoverNode,
}) => {
  const [openPath, setOpenPath] = useState<string | null>(null);
  const nodeId = `instance-${generatorId}`;

  return (
    <Stack gap="sm" mt="sm" pl="lg">
      {entries.map((entry, index) => {
        const slash = entry.path.lastIndexOf('/');
        const dir = slash !== -1 ? entry.path.slice(0, slash + 1) : '';
        const base = slash !== -1 ? entry.path.slice(slash + 1) : entry.path;
        const isOpen = openPath === entry.path;

        return (
          <div key={entry.path}>
            {index > 0 && <Divider mb="sm" />}
            <Stack gap={8}>
              <UnstyledButton
                onClick={() =>
                  setOpenPath((prev) =>
                    prev === entry.path ? null : entry.path
                  )
                }
                onMouseEnter={() => onHoverNode?.(nodeId)}
                style={{ width: '100%' }}
              >
                <Group justify="space-between" wrap="nowrap" gap="sm">
                  <Group gap={8} wrap="nowrap" style={{ minWidth: 0 }}>
                    <IconFile
                      size={14}
                      style={{
                        color: 'var(--mantine-color-dimmed)',
                        flexShrink: 0,
                      }}
                    />
                    <Text size="xs" ff="monospace" truncate>
                      {dir && (
                        <Text span inherit c="dimmed">
                          {dir}
                        </Text>
                      )}
                      {base}
                    </Text>
                    {entry.warnings.length > 0 && (
                      <Tooltip
                        withArrow
                        multiline
                        w={240}
                        label={entry.warnings
                          .map((type) => WARNING_LABEL[type])
                          .join(' ')}
                      >
                        <IconAlertTriangle
                          size={13}
                          style={{
                            color: 'var(--mantine-color-yellow-text)',
                            flexShrink: 0,
                          }}
                        />
                      </Tooltip>
                    )}
                  </Group>
                  {isOpen ? (
                    <IconChevronDown
                      size={14}
                      style={{
                        color: 'var(--mantine-color-dimmed)',
                        flexShrink: 0,
                      }}
                    />
                  ) : (
                    <IconChevronRight
                      size={14}
                      style={{
                        color: 'var(--mantine-color-dimmed)',
                        flexShrink: 0,
                      }}
                    />
                  )}
                </Group>
              </UnstyledButton>

              {entry.writes.length > 0 && (
                <FlowRow
                  direction="write"
                  keys={entry.writes}
                  onEnterKey={(key) =>
                    onHighlightEdge?.(generatorId, key, 'write')
                  }
                  onLeaveKey={() => onHoverNode?.(nodeId)}
                />
              )}
              {entry.reads.length > 0 && (
                <FlowRow
                  direction="read"
                  keys={entry.reads}
                  onEnterKey={(key) =>
                    onHighlightEdge?.(generatorId, key, 'read')
                  }
                  onLeaveKey={() => onHoverNode?.(nodeId)}
                />
              )}

              <Collapse in={isOpen}>
                <SourcePreview generatorId={generatorId} path={entry.path} />
              </Collapse>
            </Stack>
          </div>
        );
      })}
    </Stack>
  );
};
