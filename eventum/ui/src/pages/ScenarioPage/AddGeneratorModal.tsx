import {
  Alert,
  Anchor,
  Box,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { FC, useMemo } from 'react';

import {
  useGeneratorConfigPathMutation,
  useGeneratorDirs,
} from '@/api/hooks/useGeneratorConfigs';
import { useAddGeneratorMutation, useGenerators } from '@/api/hooks/useGenerators';
import { useAddGeneratorToStartupMutation } from '@/api/hooks/useStartup';
import { GeneratorParameters } from '@/api/routes/generators/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

interface AddGeneratorModalProps {
  scenarioName: string;
}

export const AddGeneratorModal: FC<AddGeneratorModalProps> = ({
  scenarioName,
}) => {
  const form = useForm<GeneratorParameters>({
    initialValues: {
      id: '',
      path: '',
    },
    validate: {
      id: (value) => {
        if (!value) return 'Instance name is required';
        if (existingIds.includes(value)) return 'Instance with this name already exists';
        return null;
      },
      path: isNotEmpty('Project is required'),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  const {
    data: generatorDirs,
    isLoading: isGeneratorDirsLoading,
    isSuccess: isGeneratorDirsSuccess,
    isError: isGeneratorDirsError,
    error: generatorDirsError,
  } = useGeneratorDirs(false);

  const { data: generators } = useGenerators();

  const existingIds = useMemo(
    () => (generators ?? []).map((g) => g.id),
    [generators]
  );

  const addGenerator = useAddGeneratorMutation();
  const addGeneratorToStartup = useAddGeneratorToStartupMutation();
  const getGeneratorConfigPath = useGeneratorConfigPathMutation();

  function handleCreate(values: typeof form.values) {
    getGeneratorConfigPath.mutate(
      { name: values.path },
      {
        onSuccess: (resolvedPath) => {
          addGenerator.mutate(
            { id: values.id, params: { ...values, path: resolvedPath } },
            {
              onSuccess: () => {
                addGeneratorToStartup.mutate(
                  {
                    id: values.id,
                    params: {
                      ...values,
                      path: resolvedPath,
                      autostart: false,
                      scenarios: [scenarioName],
                    },
                  },
                  {
                    onSuccess: () => {
                      notifications.show({
                        title: 'Success',
                        message: `Instance "${values.id}" added to scenario`,
                        color: 'green',
                      });
                      modals.closeAll();
                    },
                    onError: (error) => {
                      notifications.show({
                        title: 'Error',
                        message: (
                          <>
                            Failed to add instance to startup
                            <ShowErrorDetailsAnchor error={error} prependDot />
                          </>
                        ),
                        color: 'red',
                      });
                    },
                  }
                );
              },
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to create instance
                      <ShowErrorDetailsAnchor error={error} prependDot />
                    </>
                  ),
                  color: 'red',
                });
              },
            }
          );
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to resolve project config path
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  if (isGeneratorDirsLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isGeneratorDirsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded} />}
          title="Failed to load list of projects"
        >
          {generatorDirsError.message}
          <ShowErrorDetailsAnchor error={generatorDirsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isGeneratorDirsSuccess) {
    return (
      <form onSubmit={form.onSubmit(handleCreate)}>
        <Stack>
          <TextInput
            label="Instance name"
            placeholder="name"
            required
            {...form.getInputProps('id')}
          />
          <Select
            label="Project"
            data={generatorDirs}
            searchable
            nothingFoundMessage="No project found"
            placeholder="Select project"
            clearable
            required
            {...form.getInputProps('path')}
          />

          <Group justify="space-between">
            <Box>
              {generatorDirs.length === 0 && (
                <Text size="sm">
                  Have no projects?{' '}
                  <Anchor size="sm" href={ROUTE_PATHS.PROJECTS}>
                    Create new
                  </Anchor>
                </Text>
              )}
            </Box>

            <Button
              disabled={!form.isValid()}
              loading={addGenerator.isPending}
              type="submit"
            >
              Add
            </Button>
          </Group>
        </Stack>
      </form>
    );
  }

  return null;
};
