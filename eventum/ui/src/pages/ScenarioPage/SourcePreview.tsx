import { CodeHighlight } from '@mantine/code-highlight';
import { Center, Loader, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { FC } from 'react';

import { getGeneratorFile } from '@/api/routes/generator-configs';

// Languages the app's shiki adapter loads (see App.tsx). Anything else falls
// back to plaintext so CodeHighlight never throws on an unregistered grammar.
const LOADED_LANGS = new Set([
  'csv',
  'jinja',
  'json',
  'log',
  'markdown',
  'python',
  'toml',
  'tsv',
  'xml',
  'yaml',
]);
const LANG_ALIAS: Record<string, string> = {
  yml: 'yaml',
  md: 'markdown',
  txt: 'log',
};

/** Highlight `.jinja` templates with the jinja grammar (so the state logic
 *  reads as code); fall back to the file's base format otherwise, or
 *  plaintext for anything shiki does not load. */
function previewLanguage(path: string): string {
  if (/\.jinja$/i.test(path)) return 'jinja';
  const dot = path.lastIndexOf('.');
  const ext = dot !== -1 ? path.slice(dot + 1).toLowerCase() : '';
  const lang = LANG_ALIAS[ext] ?? ext;
  return LOADED_LANGS.has(lang) ? lang : 'text';
}

interface SourcePreviewProps {
  generatorId: string;
  path: string;
}

/**
 * Inline, syntax-highlighted source of one template - shown in place under
 * its entry instead of a modal, so the read/write context stays visible.
 * Fetches lazily; the caller mounts it only while the entry is expanded.
 */
export const SourcePreview: FC<SourcePreviewProps> = ({
  generatorId,
  path,
}) => {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['generator-file-preview', generatorId, path],
    queryFn: () => getGeneratorFile(generatorId, path),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Center py="md">
        <Loader size="xs" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Text size="xs" c="red">
        Failed to load template:{' '}
        {error instanceof Error ? error.message : 'unknown error'}
      </Text>
    );
  }

  if (data === undefined) return null;

  return (
    <CodeHighlight
      code={data}
      language={previewLanguage(path)}
      styles={{
        code: { fontSize: 12 },
        pre: { maxHeight: 320, overflowY: 'auto' },
      }}
    />
  );
};
