import {
  Alert,
  Button,
  Group,
  Skeleton,
  Stack,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { FC, useMemo } from 'react';
import YAML from 'yaml';

import {
  useGeneratorFileTree,
  useUploadGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { flattenFileTree } from '@/api/routes/generator-configs/modules/file-tree';
import { TimePatternConfig } from '@/api/routes/generator-configs/schemas/plugins/input/configs/time_patterns';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

interface AddNewPatternModalProps {
  onAddNewPattern: (filePath: string) => void;
}

const filePathPattern = /^[^*"<>|?:\\]+$/;

const defaultTimePatternContent = YAML.stringify({
  label: 'Time pattern description',
  oscillator: {
    start: '00:00',
    end: 'never',
    period: 1,
    unit: 'days',
  },
  multiplier: {
    ratio: 1000,
  },
  randomizer: {
    deviation: 0.25,
    direction: 'mixed',
    sampling: 1024,
  },
  spreader: {
    distribution: 'beta',
    parameters: {
      a: 15,
      b: 15,
    },
  },
} as TimePatternConfig);

export const AddNewPatternModal: FC<AddNewPatternModalProps> = ({
  onAddNewPattern,
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
      return flattenFileTree(fileTree, true).filter(
        (file) => file.endsWith('.yml') || file.endsWith('.yaml')
      );
    } else {
      return [];
    }
  }, [fileTree, isFileTreeSuccess]);

  const form = useForm<{ filePath: string }>({
    initialValues: {
      filePath: '',
    },
    validate: {
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

        if (!(value.endsWith('.yaml') || value.endsWith('.yml'))) {
          return 'File extension must be .yaml or .yml';
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

  const uploadFile = useUploadGeneratorFileMutation();

  function handleAddFile(values: typeof form.values) {
    uploadFile.mutate(
      {
        name: projectName,
        filepath: values.filePath,
        content: defaultTimePatternContent,
      },
      {
        onSuccess: (_, { filepath }) => {
          onAddNewPattern(filepath);
          modals.closeAll();
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to add time pattern
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  return (
    <form onSubmit={form.onSubmit(handleAddFile)}>
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
            label="File location"
            placeholder="relative file path"
            {...form.getInputProps('filePath', { type: 'input' })}
          />
          <Group justify="end">
            <Button disabled={!form.isValid()} type="submit">
              Add
            </Button>
          </Group>
        </Stack>
      )}
    </form>
  );
};
