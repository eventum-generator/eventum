import { Button, Group, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { FC } from 'react';

import {
  useCreateGeneratorConfigMutation,
  useUploadGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import {
  EVENT_PLUGIN_DEFAULT_ASSETS,
  EVENT_PLUGIN_DEFAULT_CONFIGS,
  INPUT_PLUGIN_DEFAULT_CONFIGS,
  OUTPUT_PLUGIN_DEFAULT_CONFIGS,
} from '@/api/routes/generator-configs/modules/plugins/registry';
import { GeneratorConfig } from '@/api/routes/generator-configs/schemas';
import { EventPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/event';
import { EventPluginName } from '@/api/routes/generator-configs/schemas/plugins/event/base-config';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

const VALID_PROJECT_NAME_PATTERN = /^[A-Za-z0-9_-]+$/;

export interface CreateProjectSubmitModalProps {
  existingProjectNames: string[];
  projectType: EventPluginName;
}

export const CreateProjectSubmitModal: FC<CreateProjectSubmitModalProps> = ({
  existingProjectNames,
  projectType,
}) => {
  const createGeneratorConfig = useCreateGeneratorConfigMutation();
  const uploadGeneratorFile = useUploadGeneratorFileMutation();

  const form = useForm({
    initialValues: {
      projectName: '',
    },
    validate: {
      projectName: (value) => {
        if (!value) return 'Project name is required';

        const isValid = VALID_PROJECT_NAME_PATTERN.test(value);

        if (!isValid) {
          return 'Only letters, digits and symbols "-" and "_" are allowed';
        }

        if (existingProjectNames.includes(value)) {
          return 'Project with such name already exists';
        }

        return null;
      },
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleCreate() {
    const generatorConfig: GeneratorConfig = {
      input: [{ timer: INPUT_PLUGIN_DEFAULT_CONFIGS.timer }],
      event: {
        [projectType]: EVENT_PLUGIN_DEFAULT_CONFIGS[projectType],
      } as EventPluginNamedConfig,
      output: [{ file: OUTPUT_PLUGIN_DEFAULT_CONFIGS.file }],
    };

    createGeneratorConfig.mutate(
      {
        name: form.values.projectName,
        config: generatorConfig,
      },
      {
        onError: (error) => {
          modals.closeAll();

          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to create new project
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
        onSuccess: () => {
          const asset = EVENT_PLUGIN_DEFAULT_ASSETS[projectType];

          uploadGeneratorFile.mutate(
            {
              name: form.values.projectName,
              filepath: asset.path,
              content: asset.content,
            },
            {
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to add initial assets to project.{' '}
                      <ShowErrorDetailsAnchor error={error} />
                    </>
                  ),
                  color: 'red',
                });
              },
            }
          );

          modals.closeAll();

          notifications.show({
            title: 'Success',
            message: 'Project is created',
            color: 'green',
          });
        },
      }
    );
  }

  return (
    <form onSubmit={form.onSubmit(handleCreate)}>
      <Stack>
        <TextInput
          label="Project name"
          {...form.getInputProps('projectName')}
        />
        <Group justify="end">
          <Button
            loading={
              createGeneratorConfig.isPending || uploadGeneratorFile.isPending
            }
            disabled={!form.isDirty() || !form.isValid()}
            type="submit"
          >
            Create
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
