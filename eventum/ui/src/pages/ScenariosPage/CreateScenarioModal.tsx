import {
  Alert,
  Box,
  Button,
  Center,
  Checkbox,
  Container,
  Group,
  Loader,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useStartupGenerators } from '@/api/hooks/useStartup';
import { updateGeneratorInStartup } from '@/api/routes/startup';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface FormValues {
  name: string;
  selectedGeneratorIds: string[];
}

export const CreateScenarioModal = () => {
  const queryClient = useQueryClient();

  const {
    data: startupEntries,
    isLoading,
    isError,
    error,
    isSuccess,
  } = useStartupGenerators();

  const existingScenarios = new Set(
    (startupEntries ?? []).flatMap((entry) => entry.scenarios ?? [])
  );

  const form = useForm<FormValues>({
    initialValues: {
      name: '',
      selectedGeneratorIds: [],
    },
    validate: {
      name: (value) => {
        if (!value.trim()) {
          return 'Scenario name is required';
        }
        if (existingScenarios.has(value.trim())) {
          return 'Scenario with this name already exists';
        }
        return null;
      },
      selectedGeneratorIds: isNotEmpty('Select at least one generator'),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  const createScenario = useMutation({
    mutationFn: async ({
      scenarioName,
      generatorIds,
      entries,
    }: {
      scenarioName: string;
      generatorIds: string[];
      entries: StartupGeneratorParametersList;
    }) => {
      const affectedEntries = entries.filter((entry) =>
        generatorIds.includes(entry.id)
      );

      await Promise.all(
        affectedEntries.map((entry) => {
          const updatedScenarios = [...(entry.scenarios ?? []), scenarioName];
          return updateGeneratorInStartup(entry.id, {
            ...entry,
            scenarios: updatedScenarios,
          });
        })
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['startup'] });
      notifications.show({
        title: 'Success',
        message: 'Scenario created',
        color: 'green',
      });
      modals.closeAll();
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to create scenario
            <ShowErrorDetailsAnchor error={error} prependDot />
          </>
        ),
        color: 'red',
      });
    },
  });

  function handleSubmit(values: FormValues) {
    if (!startupEntries) return;

    createScenario.mutate({
      scenarioName: values.name.trim(),
      generatorIds: values.selectedGeneratorIds,
      entries: startupEntries,
    });
  }

  if (isLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load generators"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isSuccess) {
    return (
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <TextInput
            label="Scenario name"
            placeholder="e.g. network-monitoring"
            required
            {...form.getInputProps('name')}
          />

          <Text size="sm" fw={500}>
            Generators
          </Text>

          {startupEntries.length === 0 ? (
            <Text size="sm" c="dimmed">
              No instances available. Create instances first.
            </Text>
          ) : (
            <Checkbox.Group {...form.getInputProps('selectedGeneratorIds')}>
              <Stack gap="xs">
                {startupEntries.map((entry) => (
                  <Checkbox key={entry.id} value={entry.id} label={entry.id} />
                ))}
              </Stack>
            </Checkbox.Group>
          )}

          <Group justify="flex-end">
            <Button
              disabled={!form.isValid() || startupEntries.length === 0}
              loading={createScenario.isPending}
              type="submit"
            >
              Create
            </Button>
          </Group>
        </Stack>
      </form>
    );
  }

  return null;
};
