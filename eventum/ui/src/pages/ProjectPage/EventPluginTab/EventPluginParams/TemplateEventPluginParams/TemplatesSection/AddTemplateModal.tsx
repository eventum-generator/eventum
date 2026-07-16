import {
  Alert,
  Button,
  Group,
  Skeleton,
  Stack,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { FC, useMemo } from 'react';

import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { flattenFileTree } from '@/api/routes/generator-configs/modules/file-tree';
import { TemplateConfigForGeneralModes } from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

interface AddTemplateModalProps {
  existingTemplates: string[];
  onAdd: (
    templateName: string,
    templatePath: string,
    templateConfig: TemplateConfigForGeneralModes
  ) => void;
}

const filePathPattern = /^[^*"<>|?:\\]+$/;

export const AddTemplateModal: FC<AddTemplateModalProps> = ({
  existingTemplates,
  onAdd,
}) => {
  const { projectName } = useProjectName();
  const {
    data: fileTree,
    isLoading: isFileTreeLoading,
    isError: isFileTreeError,
    error: fileTreeError,
    isSuccess: isFileTreeSuccess,
  } = useGeneratorFileTree(projectName);

  const filesList = useMemo(() => {
    if (isFileTreeSuccess) {
      return flattenFileTree(fileTree, true).filter((file) =>
        file.endsWith('.jinja')
      );
    } else {
      return [];
    }
  }, [fileTree, isFileTreeSuccess]);

  const internalForm = useForm<{ templateName: string; filePath: string }>({
    initialValues: {
      templateName: '',
      filePath: '',
    },
    validate: {
      templateName: (value) => {
        if (value === '') {
          return 'Template name is required';
        }

        if (existingTemplates.includes(value)) {
          return 'Template with this name already exists';
        }

        return null;
      },
      filePath: (value) => {
        if (value === '') {
          return 'File path is required';
        }

        if (
          filesList
            .map((item) => item.replace(/^\.\//, ''))
            .includes(value.replace(/^\.\//, ''))
        ) {
          return 'File already exists';
        }

        if (!value.endsWith('.jinja')) {
          return 'File extension must be .jinja';
        }

        if (!filePathPattern.test(value)) {
          return 'File path contains forbidden characters';
        }

        return null;
      },
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleAddTemplate(values: typeof internalForm.values) {
    onAdd(values.templateName, values.filePath, { template: values.filePath });
  }

  return (
    <form onSubmit={internalForm.onSubmit(handleAddTemplate)}>
      {isFileTreeLoading && (
        <Stack>
          <Skeleton h="250px" animate visible />
        </Stack>
      )}

      {isFileTreeError && (
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to load list of project files"
        >
          {fileTreeError.message}
          <ShowErrorDetailsAnchor error={fileTreeError} prependDot />
        </Alert>
      )}

      {isFileTreeSuccess && (
        <Stack>
          <TextInput
            label="Template name"
            placeholder="name"
            {...internalForm.getInputProps('templateName')}
          />
          <TextInput
            label="File path"
            placeholder="path"
            {...internalForm.getInputProps('filePath')}
          />
          <Group justify="end">
            <Button disabled={!internalForm.isValid()} type="submit">
              Add
            </Button>
          </Group>
        </Stack>
      )}
    </form>
  );
};
