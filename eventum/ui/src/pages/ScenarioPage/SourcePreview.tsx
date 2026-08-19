import { CodeHighlight } from '@mantine/code-highlight';
import { Center, Loader, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { FC } from 'react';

import { getGeneratorFile } from '@/api/routes/generator-configs';

import { previewLanguage } from './preview-language';

interface SourcePreviewProps {
  generatorId: string;
  path: string;
}

/**
 * Inline, syntax-highlighted source of one template or script - shown in
 * place under its entry instead of a modal, so the read/write context stays
 * visible. Fetches lazily; the caller mounts it only while the entry is
 * expanded.
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
