import {
  Button,
  Group,
  MultiSelect,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { useMemo, useState } from 'react';

import { useAddGeneratorToScenarioMutation } from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface FormValues {
  name: string;
  instances: string[];
}

export const CreateScenarioModal = () => {
  const { data: startupEntries } = useStartupGenerators();
  const addToScenario = useAddGeneratorToScenarioMutation();
  const [isCreating, setIsCreating] = useState(false);

  const existingScenarios = useMemo(
    () =>
      new Set(
        (startupEntries ?? []).flatMap((entry) => entry.scenarios ?? []),
      ),
    [startupEntries],
  );

  const availableInstances = useMemo(
    () => (startupEntries ?? []).map((entry) => entry.id),
    [startupEntries],
  );

  const form = useForm<FormValues>({
    initialValues: {
      name: '',
      instances: [],
    },
    validate: {
      name: (value) => {
        if (!value.trim()) return 'Scenario name is required';
        if (existingScenarios.has(value.trim()))
          return 'Scenario with this name already exists';
        return null;
      },
      instances: (value) => {
        if (value.length === 0) return 'Select at least one instance';
        return null;
      },
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  async function handleSubmit(values: FormValues) {
    const name = values.name.trim();
    setIsCreating(true);

    try {
      for (const generatorId of values.instances) {
        await addToScenario.mutateAsync({ name, generatorId });
      }
      showSuccessNotification(
        'Created',
        `Scenario "${name}" created with ${values.instances.length} instance(s)`,
      );
      modals.closeAll();
    } catch (error) {
      showErrorNotification('Failed to create scenario', error as Error);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <form onSubmit={form.onSubmit((v) => void handleSubmit(v))}>
      <Stack>
        <TextInput
          label="Scenario name"
          placeholder="e.g. network-monitoring"
          required
          {...form.getInputProps('name')}
        />

        <MultiSelect
          label="Instances"
          placeholder="Select instances"
          data={availableInstances}
          searchable
          required
          nothingFoundMessage="No instances available"
          {...form.getInputProps('instances')}
        />

        {form.values.instances.length > 0 && (
          <Text size="xs" c="dimmed">
            {form.values.instances.length} instance(s) will be added to the
            scenario
          </Text>
        )}

        <Group justify="flex-end">
          <Button
            disabled={!form.isValid()}
            loading={isCreating}
            type="submit"
          >
            Create
          </Button>
        </Group>
      </Stack>
    </form>
  );
};
