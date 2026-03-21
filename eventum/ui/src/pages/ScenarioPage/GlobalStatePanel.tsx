import {
  Alert,
  Collapse,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
  UnstyledButton,
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconChevronDown,
  IconChevronRight,
  IconDatabase,
} from '@tabler/icons-react';
import { dirname } from 'pathe';
import { useEffect, useMemo, useState } from 'react';

import { GlobalStateInspector } from './GlobalStateInspector';
import { GlobalsUsage } from '@/api/routes/scenarios/schemas';

interface WriterEntry {
  generatorId: string;
  generatorName: string;
  template: string;
  line: number;
  snippet: string;
}

interface ReaderEntry {
  generatorId: string;
  generatorName: string;
  template: string;
  line: number;
  snippet: string;
}

interface KeyInfo {
  writers: WriterEntry[];
  readers: ReaderEntry[];
}

function uniqueTemplateCount(info: KeyInfo): number {
  const templates = new Set<string>();
  for (const w of info.writers) templates.add(`${w.generatorId}:${w.template}`);
  for (const r of info.readers) templates.add(`${r.generatorId}:${r.template}`);
  return templates.size;
}

function uniqueWriterNames(info: KeyInfo): string[] {
  return [...new Set(info.writers.map((w) => w.generatorId))];
}

function uniqueReaderNames(info: KeyInfo): string[] {
  return [...new Set(info.readers.map((r) => r.generatorId))];
}

function flowSummary(info: KeyInfo): string {
  const writers = uniqueWriterNames(info);
  const readers = uniqueReaderNames(info);

  if (writers.length > 0 && readers.length > 0) {
    return `${writers.join(', ')} → ${readers.join(', ')}`;
  }
  if (writers.length > 0) {
    return `${writers.join(', ')} → (no readers)`;
  }
  if (readers.length > 0) {
    return `(no writers) → ${readers.join(', ')}`;
  }
  return '';
}

export interface GlobalStatePanelProps {
  generatorNames: string[];
  generatorPaths: Map<string, string>;
  globalsUsageResults: {
    data?: GlobalsUsage;
    isLoading: boolean;
  }[];
  selectedKey?: string | null;
  onKeyHover?: (keyName: string | null) => void;
}

export const GlobalStatePanel = ({
  generatorNames,
  generatorPaths,
  globalsUsageResults,
  selectedKey,
  onKeyHover,
}: GlobalStatePanelProps) => {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  useEffect(() => {
    if (selectedKey) {
      setExpandedKey(selectedKey);
    }
  }, [selectedKey]);

  function handleKeyHover(keyName: string | null) {
    onKeyHover?.(keyName);
  }

  const isLoading = globalsUsageResults.some((r) => r.isLoading);

  const keyMap = useMemo(() => {
    const map = new Map<string, KeyInfo>();

    for (const [i, generatorId] of generatorNames.entries()) {
      const usage = globalsUsageResults[i]?.data;
      if (!usage) continue;

      const path = generatorPaths.get(generatorId) ?? '';
      const generatorName = dirname(path);

      for (const ref of usage.writes) {
        if (!map.has(ref.key)) {
          map.set(ref.key, { writers: [], readers: [] });
        }
        map.get(ref.key)!.writers.push({
          generatorId,
          generatorName,
          template: ref.template,
          line: ref.line,
          snippet: ref.snippet,
        });
      }

      for (const ref of usage.reads) {
        if (!map.has(ref.key)) {
          map.set(ref.key, { writers: [], readers: [] });
        }
        map.get(ref.key)!.readers.push({
          generatorId,
          generatorName,
          template: ref.template,
          line: ref.line,
          snippet: ref.snippet,
        });
      }
    }

    return map;
  }, [generatorNames, generatorPaths, globalsUsageResults]);

  const sortedKeys = useMemo(
    () => [...keyMap.keys()].sort((a, b) => a.localeCompare(b)),
    [keyMap],
  );

  const orphanedReads = useMemo(
    () =>
      sortedKeys.filter((key) => {
        const info = keyMap.get(key)!;
        return info.readers.length > 0 && info.writers.length === 0;
      }),
    [sortedKeys, keyMap],
  );

  const unusedWrites = useMemo(
    () =>
      sortedKeys.filter((key) => {
        const info = keyMap.get(key)!;
        return info.writers.length > 0 && info.readers.length === 0;
      }),
    [sortedKeys, keyMap],
  );

  function toggleKey(key: string) {
    setExpandedKey((prev) => (prev === key ? null : key));
  }

  return (
    <Paper withBorder p="md" h="100%">
      <Stack gap="sm">
        <Group gap="xs">
          <IconDatabase size={16} />
          <Title order={5} fw="normal">
            Global State
          </Title>
        </Group>

        {isLoading ? (
          <Group justify="center" py="md">
            <Loader size="sm" />
          </Group>
        ) : sortedKeys.length === 0 ? (
          <Text size="sm" c="dimmed">
            No global state keys detected.
          </Text>
        ) : (
          <Stack gap="sm">
            {sortedKeys.map((key) => {
              const info = keyMap.get(key)!;
              const isExpanded = expandedKey === key;
              const templateCount = uniqueTemplateCount(info);
              const summary = flowSummary(info);

              return (
                <Paper
                  key={key}
                  withBorder
                  p={0}
                  radius="sm"
                  bg="var(--mantine-color-default)"
                  onMouseEnter={() => handleKeyHover(key)}
                  onMouseLeave={() => handleKeyHover(null)}
                >
                  <UnstyledButton
                    w="100%"
                    p="xs"
                    onClick={() => toggleKey(key)}
                  >
                    <Stack gap={2}>
                      <Group gap="xs" wrap="nowrap">
                        {isExpanded ? (
                          <IconChevronDown size={14} />
                        ) : (
                          <IconChevronRight size={14} />
                        )}
                        <Text size="sm" fw={600} ff="monospace">
                          {key}
                        </Text>
                      </Group>

                      <Text size="xs" c="dimmed" pl={22} truncate>
                        {summary}
                      </Text>

                      <Text size="xs" c="dimmed" pl={22}>
                        Used in {templateCount} template
                        {templateCount !== 1 ? 's' : ''}
                      </Text>
                    </Stack>
                  </UnstyledButton>

                  <Collapse in={isExpanded}>
                    <GlobalStateInspector
                      keyName={key}
                      writers={info.writers}
                      readers={info.readers}
                    />
                  </Collapse>
                </Paper>
              );
            })}
          </Stack>
        )}

        {(orphanedReads.length > 0 || unusedWrites.length > 0) && (
          <Stack gap="xs" mt="sm">
            {orphanedReads.map((key) => (
              <Alert
                key={`orphan-${key}`}
                variant="light"
                color="yellow"
                icon={<IconAlertTriangle size={16} />}
                p="xs"
              >
                <Text size="xs">
                  <Text span fw={600} ff="monospace">
                    {key}
                  </Text>{' '}
                  is read but never written in this scenario.
                </Text>
              </Alert>
            ))}

            {unusedWrites.map((key) => (
              <Alert
                key={`unused-${key}`}
                variant="light"
                color="yellow"
                icon={<IconAlertTriangle size={16} />}
                p="xs"
              >
                <Text size="xs">
                  <Text span fw={600} ff="monospace">
                    {key}
                  </Text>{' '}
                  is written but never read in this scenario.
                </Text>
              </Alert>
            ))}
          </Stack>
        )}
      </Stack>
    </Paper>
  );
};
