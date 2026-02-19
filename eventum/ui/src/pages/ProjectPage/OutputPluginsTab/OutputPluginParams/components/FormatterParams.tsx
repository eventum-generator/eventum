import {
  Center,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Textarea,
} from '@mantine/core';
import { IconBraces, IconFile } from '@tabler/icons-react';
import { FC, ReactNode, useState } from 'react';

import { ProjectFileSelect } from '../../../components/ProjectFileSelect';
import {
  Format,
  FormatterConfig,
} from '@/api/routes/generator-configs/schemas/plugins/output/formatters';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface FormatterParamsProps {
  value: FormatterConfig | undefined;
  onChange: (config: FormatterConfig | undefined) => void;
}

export const FormatterParams: FC<FormatterParamsProps> = ({
  value,
  onChange,
}) => {
  const [templateSourceType, setTemplateSourceType] = useState<
    'template' | 'template-path'
  >('template');

  return (
    <Stack gap="xs">
      <Select
        label={
          <LabelWithTooltip label="Format" tooltip="Target format of content" />
        }
        placeholder="format"
        data={[
          Format.EventumHTTPInput,
          Format.JSON,
          Format.JSONBatch,
          Format.Plain,
          Format.Template,
          Format.TemplateBatch,
        ]}
        clearable
        value={value?.format ?? null}
        onChange={(value) => {
          if (value === null) {
            // eslint-disable-next-line unicorn/no-useless-undefined
            onChange(undefined);
          } else {
            onChange({ format: value as Format });
          }
        }}
      />

      {(value?.format === Format.JSON ||
        value?.format === Format.JSONBatch) && (
        <NumberInput
          label={
            <LabelWithTooltip
              label="Indent"
              tooltip="Indentation size of JSON content"
            />
          }
          placeholder="number"
          min={0}
          step={1}
          allowDecimal={false}
          value={value.indent ?? 0}
          onChange={(val) => {
            onChange({
              format: value.format,
              indent: typeof val === 'number' ? val : 0,
            });
          }}
        />
      )}

      {(value?.format === Format.Template ||
        value?.format === Format.TemplateBatch) && (
        <Stack gap="xs">
          <SegmentedControl
            data={
              [
                {
                  label: (
                    <Center>
                      <Group gap="4px">
                        <IconBraces size={14} />
                        <span>Template</span>
                      </Group>
                    </Center>
                  ),
                  value: 'template',
                },
                {
                  label: (
                    <Center>
                      <Group gap="4px">
                        <IconFile size={14} />
                        <span>Template file</span>
                      </Group>
                    </Center>
                  ),
                  value: 'template-path',
                },
              ] as const satisfies {
                label: ReactNode;
                value: typeof templateSourceType;
              }[]
            }
            value={templateSourceType}
            onChange={(value) =>
              setTemplateSourceType(value as typeof templateSourceType)
            }
          />
          {templateSourceType === 'template' && (
            <Textarea
              label={
                <LabelWithTooltip
                  label="Template"
                  tooltip="Jinja template content"
                />
              }
              placeholder="template code"
              description="To access original event(s) use `event` or `events` variables
              in template for `template` and `template-batch` modes correspondingly"
              minRows={3}
              autosize
              value={value.template ?? ''}
              onChange={(e) => {
                onChange({
                  format: value.format,
                  template: e.currentTarget.value,
                });
              }}
            />
          )}
          {templateSourceType === 'template-path' && (
            <ProjectFileSelect
              label={
                <LabelWithTooltip
                  label="Template path"
                  tooltip="Path to file with template content"
                />
              }
              clearable
              searchable
              error={!value?.template_path ? 'Template path is required' : null}
              value={value?.template_path ?? null}
              onChange={(val) => {
                onChange({
                  format: value.format,
                  template_path: val ?? undefined,
                });
              }}
              extensions={['.jinja']}
            />
          )}
        </Stack>
      )}
    </Stack>
  );
};
