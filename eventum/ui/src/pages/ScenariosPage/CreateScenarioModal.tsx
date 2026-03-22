import { Button, Group, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { useStartupGenerators } from '@/api/hooks/useStartup';
import { ROUTE_PATHS } from '@/routing/paths';

interface FormValues {
  name: string;
}

export const CreateScenarioModal = () => {
  const navigate = useNavigate();

  const { data: startupEntries } = useStartupGenerators();

  const existingScenarios = useMemo(
    () =>
      new Set(
        (startupEntries ?? []).flatMap((entry) => entry.scenarios ?? []),
      ),
    [startupEntries],
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
    modals.closeAll();
    void navigate(`${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(trimmed)}`);
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
