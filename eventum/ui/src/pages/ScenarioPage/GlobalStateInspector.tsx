import { Anchor, Code, Divider, Group, Stack, Text } from '@mantine/core';
import { FC, useState } from 'react';

import { TemplatePreviewModal } from './TemplatePreviewModal';

export interface GlobalStateInspectorProps {
  keyName: string;
  writers: {
    generatorId: string;
    generatorName: string;
    template: string;
    line: number;
    snippet: string;
  }[];
  readers: {
    generatorId: string;
    generatorName: string;
    template: string;
    line: number;
    snippet: string;
  }[];
}

export const GlobalStateInspector: FC<GlobalStateInspectorProps> = ({
  writers,
  readers,
}) => {
  const [preview, setPreview] = useState<{
    generatorName: string;
    templatePath: string;
  } | null>(null);

  return (
    <>
      <Stack gap="sm" p="sm" pt={0}>
        {writers.length > 0 && (
          <>
            <Divider
              label={
                <Text size="xs" fw={500}>
                  Writers
                </Text>
              }
              labelPosition="left"
            />
            <Stack gap="xs">
              {writers.map((w, i) => (
                <Stack key={`w-${i}`} gap={2}>
                  <Group gap="xs" justify="space-between" wrap="nowrap">
                    <Text size="xs" c="dimmed" truncate>
                      {w.generatorId} &middot; {w.template}:{w.line}
                    </Text>
                    <Anchor
                      size="xs"
                      component="button"
                      onClick={() =>
                        setPreview({
                          generatorName: w.generatorName,
                          templatePath: w.template,
                        })
                      }
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      View template
                    </Anchor>
                  </Group>
                  <Code block style={{ fontSize: 11 }}>
                    {w.snippet}
                  </Code>
                </Stack>
              ))}
            </Stack>
          </>
        )}

        {readers.length > 0 && (
          <>
            <Divider
              label={
                <Text size="xs" fw={500}>
                  Readers
                </Text>
              }
              labelPosition="left"
            />
            <Stack gap="xs">
              {readers.map((r, i) => (
                <Stack key={`r-${i}`} gap={2}>
                  <Group gap="xs" justify="space-between" wrap="nowrap">
                    <Text size="xs" c="dimmed" truncate>
                      {r.generatorId} &middot; {r.template}:{r.line}
                    </Text>
                    <Anchor
                      size="xs"
                      component="button"
                      onClick={() =>
                        setPreview({
                          generatorName: r.generatorName,
                          templatePath: r.template,
                        })
                      }
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      View template
                    </Anchor>
                  </Group>
                  <Code block style={{ fontSize: 11 }}>
                    {r.snippet}
                  </Code>
                </Stack>
              ))}
            </Stack>
          </>
        )}
      </Stack>

      {preview && (
        <TemplatePreviewModal
          opened={preview !== null}
          onClose={() => setPreview(null)}
          generatorName={preview.generatorName}
          templatePath={preview.templatePath}
        />
      )}
    </>
  );
};
