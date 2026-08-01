import {
  Alert,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { FC } from 'react';

import {
  useAddGeneratorMutation,
  useGenerator,
} from '@/api/hooks/useGenerators';
import {
  useAddGeneratorToStartupMutation,
  useStartupGenerator,
} from '@/api/hooks/useStartup';
import { GeneratorParametersSchema } from '@/api/routes/generators/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface CloneInstanceModalProps {
  sourceInstanceId: string;
  existingInstanceIds: string[];
}

function suggestCloneName(sourceId: string, existingIds: string[]): string {
  const base = `${sourceId}-clone`;

  if (!existingIds.includes(base)) {
    return base;
  }

  let suffix = 2;
  while (existingIds.includes(`${base}-${suffix}`)) {
    suffix += 1;
  }

  return `${base}-${suffix}`;
}

export const CloneInstanceModal: FC<CloneInstanceModalProps> = ({
  sourceInstanceId,
  existingInstanceIds,
}) => {
  const form = useForm<{ id: string }>({
    initialValues: {
      id: suggestCloneName(sourceInstanceId, existingInstanceIds),
    },
    validate: {
      id: (value) => {
        if (!value) {
          return 'Instance name is required';
        }
        if (existingInstanceIds.includes(value)) {
          return 'Instance with this name already exists';
        }

        return null;
      },
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  const {
    data: generatorParams,
    isLoading: isGeneratorParamsLoading,
    isError: isGeneratorParamsError,
    error: generatorParamsError,
    isSuccess: isGeneratorParamsSuccess,
  } = useGenerator(sourceInstanceId);

  const {
    data: startupGeneratorParams,
    isLoading: isStartupGeneratorParamsLoading,
    isError: isStartupGeneratorParamsError,
    error: startupGeneratorParamsError,
    isSuccess: isStartupGeneratorParamsSuccess,
  } = useStartupGenerator(sourceInstanceId);

  const addGenerator = useAddGeneratorMutation();
  const addGeneratorToStartup = useAddGeneratorToStartupMutation();

  function handleCloneInstance(values: typeof form.values) {
    if (generatorParams === undefined || startupGeneratorParams === undefined) {
      return;
    }

    const params: StartupGeneratorParameters = {
      ...generatorParams,
      autostart: startupGeneratorParams.autostart,
      scenarios: startupGeneratorParams.scenarios ?? [],
      id: values.id,
    };

    addGenerator.mutate(
      { id: values.id, params: GeneratorParametersSchema.parse(params) },
      {
        onSuccess: () => {
          addGeneratorToStartup.mutate(
            { id: values.id, params },
            {
              onSuccess: () => {
                notifications.show({
                  title: 'Success',
                  message: 'Instance is cloned',
                  color: 'green',
                });
                modals.closeAll();
              },
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to add instance definition to startup
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
                Failed to clone instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  if (isGeneratorParamsLoading || isStartupGeneratorParamsLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isGeneratorParamsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to get instance parameters"
        >
          {generatorParamsError.message}
          <ShowErrorDetailsAnchor error={generatorParamsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isStartupGeneratorParamsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to get startup instance parameters"
        >
          {startupGeneratorParamsError.message}
          <ShowErrorDetailsAnchor
            error={startupGeneratorParamsError}
            prependDot
          />
        </Alert>
      </Container>
    );
  }

  if (isGeneratorParamsSuccess && isStartupGeneratorParamsSuccess) {
    return (
      <form onSubmit={form.onSubmit(handleCloneInstance)}>
        <Stack>
          <Text size="sm" c="dimmed">
            Cloning <b>{sourceInstanceId}</b> with all its parameters.
          </Text>

          <TextInput
            label="New instance name"
            placeholder="name"
            required
            {...form.getInputProps('id')}
          />

          <Group justify="end">
            <Button
              disabled={!form.isValid()}
              loading={
                addGenerator.isPending || addGeneratorToStartup.isPending
              }
              type="submit"
            >
              Clone
            </Button>
          </Group>
        </Stack>
      </form>
    );
  }

  return null;
};
