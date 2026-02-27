import {
  ActionIcon,
  Button,
  Center,
  Group,
  JsonInput,
  Kbd,
  SegmentedControl,
  Stack,
  Switch,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconFile, IconList } from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC, ReactNode } from 'react';

import {
  SampleConfig,
  SampleConfigSchema,
  SampleType,
} from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ProjectFileSelect } from '@/pages/ProjectPage/components/ProjectFileSelect';

interface SamplesParamsProps {
  value: SampleConfig;
  onChange: (value: SampleConfig) => void;
  onDelete: () => void;
}

export const SamplesParams: FC<SamplesParamsProps> = ({
  value,
  onChange,
  onDelete,
}) => {
  const form = useForm<SampleConfig>({
    initialValues: value,
    validate: zod4Resolver(SampleConfigSchema),
    onValuesChange: onChange,
    validateInputOnChange: true,
  });

  return (
    <Stack gap="xs">
      <Stack gap="4px">
        <SegmentedControl
          data={
            [
              {
                label: (
                  <Center>
                    <Group gap="4px">
                      <IconList size={14} />
                      <span>Items</span>
                    </Group>
                  </Center>
                ),
                value: SampleType.Items,
              },
              {
                label: (
                  <Center>
                    <Group gap="4px">
                      <IconFile size={14} />
                      <span>CSV</span>
                    </Group>
                  </Center>
                ),
                value: SampleType.CSV,
              },
              {
                label: (
                  <Center>
                    <Group gap="4px">
                      <IconFile size={14} />
                      <span>JSON</span>
                    </Group>
                  </Center>
                ),
                value: SampleType.JSON,
              },
            ] as const satisfies { label: ReactNode; value: SampleType }[]
          }
          {...form.getInputProps('type')}
          onChange={(value) => {
            const sampleType = value as SampleType;

            form.setValues({
              type: sampleType,
              source: undefined!,
              delimiter: undefined!,
              quotechar: undefined!,
              header: undefined!,
            });

            if (sampleType === SampleType.CSV) {
              form.setValues({
                header: true,
                delimiter: ',',
                quotechar: '"',
              });
            } else if (sampleType === SampleType.Items) {
              form.setValues({
                source: ['item1', 'item2', 'item3'],
              });
            }

            form.clearErrors();
          }}
        />
        {form.values.type == SampleType.Items && (
          <JsonInput
            label="Sample items"
            description="Each element of list is a sample's item"
            placeholder="[ ... ]"
            validationError="Invalid JSON"
            minRows={4}
            autosize
            required
            defaultValue={JSON.stringify(form.values.source ?? '')}
            onChange={(value) => {
              if (value === '') {
                form.setFieldValue('source', undefined!);
              }

              let parsedValue: unknown;
              try {
                parsedValue = JSON.parse(value);
              } catch {
                return;
              }

              if (!Array.isArray(parsedValue)) {
                return;
              }

              form.setFieldValue('source', parsedValue);
            }}
            error={form.errors.source}
          />
        )}
        {form.values.type == SampleType.CSV && (
          <Stack gap="xs">
            <ProjectFileSelect
              label={<LabelWithTooltip label="Source" tooltip="CSV file" />}
              placeholder=".csv .tsv"
              clearable
              searchable
              required
              {...form.getInputProps('source')}
              value={form.values.source ?? null}
              onChange={(value) => {
                form.setFieldValue('source', value ?? undefined!);
              }}
              extensions={['.csv', '.tsv']}
            />
            <Group gap="xs" align="start" wrap="nowrap">
              <TextInput
                label={
                  <LabelWithTooltip
                    label="Delimiter"
                    tooltip="Delimiter used in CSV file"
                  />
                }
                w="100%"
                rightSection={
                  <Group wrap="nowrap" gap="2px">
                    <ActionIcon
                      variant="transparent"
                      title="Set tabulation as delimiter"
                      onClick={() => {
                        form.setFieldValue('delimiter', '\t');
                      }}
                    >
                      <Kbd>\t</Kbd>
                    </ActionIcon>
                  </Group>
                }
                rightSectionWidth={40}
                {...form.getInputProps('delimiter')}
                value={form.values.delimiter ?? ''}
                onChange={(event) => {
                  form.setFieldValue(
                    'delimiter',
                    event.currentTarget.value !== ''
                      ? event.currentTarget.value
                      : undefined!
                  );
                }}
              />
              <TextInput
                label={
                  <LabelWithTooltip
                    label="Quote char"
                    tooltip={`Character used to quote fields containing the delimiter (RFC 4180). Default is value is '"' (double quote)`}
                  />
                }
                w="100%"
                maxLength={1}
                {...form.getInputProps('quotechar')}
                value={form.values.quotechar ?? ''}
                onChange={(event) => {
                  form.setFieldValue(
                    'quotechar',
                    event.currentTarget.value !== ''
                      ? event.currentTarget.value
                      : undefined!
                  );
                }}
              />
              <Switch
                mt="xl"
                label={
                  <LabelWithTooltip
                    label="Header"
                    tooltip="Whether CSV sample includes header on its first line"
                  />
                }
                {...form.getInputProps('header', { type: 'checkbox' })}
              />
            </Group>
          </Stack>
        )}

        {form.values.type == SampleType.JSON && (
          <ProjectFileSelect
            label={<LabelWithTooltip label="Source" tooltip="JSON file" />}
            placeholder=".json"
            clearable
            searchable
            required
            {...form.getInputProps('source')}
            value={form.values.source ?? null}
            onChange={(value) => {
              form.setFieldValue('source', value ?? undefined!);
            }}
            extensions={['.json']}
          />
        )}
      </Stack>
      <Button variant="default" onClick={onDelete}>
        Remove
      </Button>
    </Stack>
  );
};
