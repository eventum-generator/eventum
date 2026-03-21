import { Button, Group, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { useStartupGenerators } from '@/api/hooks/useStartup';

interface FormValues {
  name: string;
}

export const CreateScenarioModal = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: startupEntries } = useStartupGenerators();

  const existingScenarios = new Set(
    (startupEntries ?? []).flatMap((entry) => entry.scenarios ?? [])
  );

  const form = useForm<FormValues>({
    initialValues: {
      name: '',
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
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleSubmit(values: FormValues) {
    const trimmed = values.name.trim();

    // No generators to update — just navigate to the new scenario page
    void queryClient.invalidateQueries({ queryKey: ['startup'] });
    notifications.show({
      title: 'Success',
      message: 'Scenario created',
      color: 'green',
    });
    modals.closeAll();
    void navigate(`/scenarios/${encodeURIComponent(trimmed)}`);
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack>
        <TextInput
          label="Scenario name"
          placeholder="e.g. network-monitoring"
          required
          {...form.getInputProps('name')}
        />

        <Group justify="flex-end">
          <Button disabled={!form.isValid()} type="submit">
            Create
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
