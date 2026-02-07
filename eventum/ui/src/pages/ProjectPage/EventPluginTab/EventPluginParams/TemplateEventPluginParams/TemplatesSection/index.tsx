import {
  ActionIcon,
  Group,
  MultiSelect,
  Select,
  Stack,
  Text,
} from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconPlus } from '@tabler/icons-react';
import { FC, useState } from 'react';

import { AddTemplateModal } from './AddTemplateModal';
import { RemoveTemplateModal } from './RemoveTemplateModal';
import { TemplateParams } from './TemplateParams';
import {
  useDeleteGeneratorFileMutation,
  useUploadGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import {
  TemplateConfigForChanceMode,
  TemplateConfigForFSMMode,
  TemplateConfigForGeneralModes,
  TemplateEventPluginConfig,
  TemplateEventPluginConfigForChainMode,
  TemplatePickingMode,
} from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

interface TemplatesSectionProps {
  form: UseFormReturnType<TemplateEventPluginConfig>;
}

export const TemplatesSection: FC<TemplatesSectionProps> = ({ form }) => {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const existingTemplates = form
    .getValues()
    .templates.map((item) => Object.keys(item)[0]!);

  const uploadFile = useUploadGeneratorFileMutation();
  const deleteFile = useDeleteGeneratorFileMutation();
  const { projectName } = useProjectName();

  function handleAddNewTemplate(
    templateName: string,
    templatePath: string,
    templateConfig: TemplateConfigForGeneralModes
  ) {
    uploadFile.mutate(
      {
        name: projectName,
        filepath: templatePath,
        content: 'Describe event',
      },
      {
        onSuccess: () => {
          form.setFieldValue('templates', (value) => [
            ...value,
            { [templateName]: templateConfig },
          ]);
          setSelectedTemplate(templateName);
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to add template file
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );

    modals.closeAll();
  }

  function handleDeleteTemplate(
    templatePath: string | undefined,
    templateName: string,
    isRemoveFile: boolean
  ) {
    form.setFieldValue('templates', (prevValue) => {
      const selectedTemplateIndex = prevValue.findIndex(
        (item) => Object.keys(item)[0] === templateName
      );

      return [
        ...prevValue.slice(0, selectedTemplateIndex),
        ...prevValue.slice(selectedTemplateIndex + 1),
      ];
    });

    if (isRemoveFile && templatePath !== undefined) {
      deleteFile.mutate(
        { name: projectName, filepath: templatePath },
        {
          onError: (error) => {
            notifications.show({
              title: 'Error',
              message: (
                <>
                  Failed to delete template file
                  <ShowErrorDetailsAnchor error={error} prependDot />
                </>
              ),
              color: 'red',
            });
          },
        }
      );
    }

    modals.closeAll();
    setSelectedTemplate(null);
  }

  return (
    <Stack gap="xs">
      <Stack gap="4px">
        <Text size="sm" fw="bold">
          Templates
        </Text>
        <Select
          label={
            <LabelWithTooltip
              label="Template picking mode"
              tooltip="Algorithm of how template is picked for each timestamp"
            />
          }
          clearable
          searchable
          required
          data={[
            {
              label: 'All',
              value: TemplatePickingMode.All,
            },
            {
              label: 'Any',
              value: TemplatePickingMode.Any,
            },
            {
              label: 'Chance',
              value: TemplatePickingMode.Chance,
            },
            {
              label: 'Spin',
              value: TemplatePickingMode.Spin,
            },
            {
              label: 'Chain',
              value: TemplatePickingMode.Chain,
            },
            {
              label: 'FSM',
              value: TemplatePickingMode.FSM,
            },
          ]}
          value={form.getValues().mode ?? null}
          onChange={(value) => {
            form.setFieldValue('mode', (prevValue) => {
              // remove not actual parameters of previous picking mode from state
              form.setFieldValue('templates', (prevTemplatesValue) => {
                const newValue = [...prevTemplatesValue];

                for (const templateItem of newValue) {
                  const templateName = Object.keys(templateItem)[0]!;
                  const template = templateItem[templateName];

                  if (prevValue === TemplatePickingMode.Chance) {
                    (template as TemplateConfigForChanceMode).chance =
                      undefined!;
                  } else if (prevValue === TemplatePickingMode.FSM) {
                    (template as TemplateConfigForFSMMode).initial = undefined!;
                    (template as TemplateConfigForFSMMode).transitions =
                      undefined!;
                  }
                }

                if (prevValue === TemplatePickingMode.Chain) {
                  form.setFieldValue('chain', undefined!);
                }

                return newValue;
              });

              return (value as TemplatePickingMode) ?? undefined;
            });
          }}
          error={form.errors.mode}
        />
      </Stack>

      {form.getValues().mode === TemplatePickingMode.Chain && (
        <MultiSelect
          label={
            <LabelWithTooltip
              label="Chain"
              tooltip="Sequence of template names defining order of picking templates"
            />
          }
          data={existingTemplates}
          clearable
          searchable
          hidePickedOptions
          required
          {...form.getInputProps('chain')}
          value={
            (form.values as TemplateEventPluginConfigForChainMode).chain ?? []
          }
          onChange={(value) => {
            form.setFieldValue('chain', value.length > 0 ? value : undefined!);
          }}
        />
      )}

      <Group align="end" wrap="nowrap" gap="xs">
        <Select
          label="Select template to edit"
          data={existingTemplates}
          value={selectedTemplate}
          onChange={setSelectedTemplate}
          searchable
          nothingFoundMessage="No templates found"
          placeholder="template name"
          w="100%"
          clearable
        />
        <ActionIcon
          title="Add new template"
          size="lg"
          variant="default"
          onClick={() => {
            modals.open({
              title: 'Adding template',
              children: (
                <ProjectNameProvider initialProjectName={projectName}>
                  <AddTemplateModal
                    existingTemplates={existingTemplates}
                    onAdd={handleAddNewTemplate}
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

      {selectedTemplate !== null &&
        existingTemplates.includes(selectedTemplate) &&
        form.values.mode && (
          <TemplateParams
            key={selectedTemplate}
            pickingMode={form.values.mode}
            value={
              form.values.templates.find(
                (item) => Object.keys(item)[0] === selectedTemplate
              )![selectedTemplate]!
            }
            onChange={(value) => {
              form.setFieldValue('templates', (prevValue) => {
                const selectedTemplateIndex = form.values.templates.findIndex(
                  (item) => Object.keys(item)[0] === selectedTemplate
                );

                return [
                  ...prevValue.slice(0, selectedTemplateIndex),
                  {
                    [selectedTemplate]: value,
                  },
                  ...prevValue.slice(selectedTemplateIndex + 1),
                ];
              });
            }}
            onDelete={(templatePath) =>
              modals.open({
                title: 'Removing template',
                children: (
                  <RemoveTemplateModal
                    templateName={selectedTemplate}
                    filePath={templatePath}
                    onDelete={({ isRemoveFile }) =>
                      handleDeleteTemplate(
                        templatePath,
                        selectedTemplate,
                        isRemoveFile
                      )
                    }
                    isDeleting={deleteFile.isPending}
                  />
                ),
              })
            }
            existingTemplates={existingTemplates}
          />
        )}
    </Stack>
  );
};
