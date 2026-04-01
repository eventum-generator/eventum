import { Code, Loader, Modal, Stack, Text } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { FC } from 'react';

import { getGeneratorFile } from '@/api/routes/generator-configs';

interface TemplatePreviewModalProps {
  opened: boolean;
  onClose: () => void;
  generatorName: string;
  templatePath: string;
}

export const TemplatePreviewModal: FC<TemplatePreviewModalProps> = ({
  opened,
  onClose,
  generatorName,
  templatePath,
}) => {
  const {
    data: content,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['generator-file-preview', generatorName, templatePath],
    queryFn: () => getGeneratorFile(generatorName, templatePath),
    enabled: opened,
  });

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={templatePath}
      size="xl"
      styles={{
        title: { fontFamily: 'var(--mantine-font-family-monospace)' },
      }}
    >
      <Stack gap="sm">
        {isLoading && <Loader size="sm" mx="auto" />}
        {isError && (
          <Text size="sm" c="red">
            Failed to load file: {error instanceof Error ? error.message : 'Unknown error'}
          </Text>
        )}
        {content !== undefined && (
          <Code block style={{ fontSize: 12, maxHeight: 500, overflow: 'auto' }}>
            {content}
          </Code>
        )}
      </Stack>
    </Modal>
  );
};
