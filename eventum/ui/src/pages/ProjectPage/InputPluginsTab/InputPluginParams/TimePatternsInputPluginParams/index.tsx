import {
  ActionIcon,
  Group,
  Paper,
  Stack,
  TagsInput,
  Text,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { IconPlus } from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { normalize } from 'pathe';
import { FC, useState } from 'react';

import { useProjectName } from '../../../hooks/useProjectName';
import { AddNewPatternModal } from './AddNewPatternModal';
import { TimePatternParams } from './TimePatternParams';
import {
  TimePatternsInputPluginConfig,
  TimePatternsInputPluginConfigSchema,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/time_patterns';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ProjectFileMultiSelect } from '@/pages/ProjectPage/components/ProjectFileMultiSelect';
import { ProjectFileSelect } from '@/pages/ProjectPage/components/ProjectFileSelect';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';

interface TimePatternsInputPluginParamsProps {
  initialConfig: TimePatternsInputPluginConfig;
  onChange: (config: TimePatternsInputPluginConfig) => void;
}

export const TimePatternsInputPluginParams: FC<
  TimePatternsInputPluginParamsProps
> = ({ initialConfig, onChange }) => {
  const { projectName } = useProjectName();

  const form = useForm<TimePatternsInputPluginConfig>({
    initialValues: initialConfig,
    onValuesChange: onChange,
    validate: zod4Resolver(TimePatternsInputPluginConfigSchema),
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
  });

  const [selectedTimePattern, setSelectedTimePattern] = useState<string | null>(
    null
  );

  return (
    <Stack gap="xs">
      <ProjectFileMultiSelect
        label={
          <LabelWithTooltip
            label="Patterns"
            tooltip="File paths to time pattern configurations."
          />
        }
        extensions={['.yml', '.yaml']}
        clearable
        searchable
        hidePickedOptions
        required
        {...form.getInputProps('patterns')}
        value={form.getValues().patterns ?? []}
        onChange={(value) =>
          form.setFieldValue('patterns', value.length > 0 ? value : undefined!)
        }
      />
      <TagsInput
        label={
          <LabelWithTooltip
            label="Tags"
            tooltip="Tags list attached to an input plugin"
          />
        }
        placeholder="Press Enter to submit a tag"
        {...form.getInputProps('tags')}
        value={form.getValues().tags ?? []}
        onChange={(value) =>
          form.setFieldValue('tags', value.length > 0 ? value : undefined)
        }
      />

      <Paper withBorder p="sm" mt="4px">
        <Stack gap="4px">
          <Text size="sm" fw="bold">
            Pattern editor
          </Text>
          <Stack>
            <Group align="end" wrap="nowrap" gap="xs">
              <ProjectFileSelect
                label="Select pattern to edit"
                searchable
                nothingFoundMessage="No files found"
                placeholder="time pattern file"
                extensions={['.yaml', '.yml']}
                w="100%"
                value={selectedTimePattern}
                onChange={setSelectedTimePattern}
                clearable
              />
              <ActionIcon
                title="Add new pattern"
                size="lg"
                variant="default"
                onClick={() => {
                  modals.open({
                    title: 'Add new time pattern',
                    children: (
                      <ProjectNameProvider initialProjectName={projectName}>
                        <AddNewPatternModal
                          onAddNewPattern={(filePath) => {
                            const normalizedPath = normalize(filePath);
                            setSelectedTimePattern(normalizedPath);
                          }}
                        />
                      </ProjectNameProvider>
                    ),
                    size: 'md',
                  });
                }}
              >
                <IconPlus size={20} />
              </ActionIcon>
            </Group>
            {selectedTimePattern && (
              <TimePatternParams
                filePath={selectedTimePattern}
                key={selectedTimePattern}
              />
            )}
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  );
};
