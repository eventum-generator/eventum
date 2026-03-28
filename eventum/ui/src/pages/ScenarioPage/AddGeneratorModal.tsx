import {
  Alert,
  Box,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Select,
  Stack,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { FC, useMemo, useState } from 'react';

import { useAddGeneratorToScenarioMutation } from '@/api/hooks/useScenarios';
import { useStartupGenerators } from '@/api/hooks/useStartup';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface AddInstanceFormProps {
  availableEntries: StartupGeneratorParameters[];
  entryMap: Map<string, StartupGeneratorParameters>;
  isPending: boolean;
  onAdd: (entry: StartupGeneratorParameters) => void;
}

function AddInstanceForm({
  availableEntries,
  entryMap,
  isPending,
  onAdd,
}: Readonly<AddInstanceFormProps>) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <Stack>
      <Select
        label="Instance"
        data={availableEntries.map((e) => e.id)}
        searchable
        nothingFoundMessage="No instances available"
        placeholder="Select instance"
        value={selected}
        onChange={setSelected}
        disabled={isPending || availableEntries.length === 0}
      />
      <Group justify="flex-end">
        <Button
          disabled={!selected}
          loading={isPending}
          onClick={() => {
            if (!selected) return;
            const entry = entryMap.get(selected);
            if (entry) onAdd(entry);
          }}
        >
          Add
        </Button>
      </Group>
    </Stack>
  );
}

interface AddGeneratorModalProps {
  scenarioName: string;
}

export const AddGeneratorModal: FC<AddGeneratorModalProps> = ({
  scenarioName,
}) => {
  const {
    data: startupEntries,
    isLoading,
    isError,
    error,
    isSuccess,
  } = useStartupGenerators();

  const availableEntries = useMemo(() => {
    if (!startupEntries) return [];
    return startupEntries.filter(
      (entry) => !(entry.scenarios ?? []).includes(scenarioName)
    );
  }, [startupEntries, scenarioName]);

  const entryMap = useMemo(() => {
    const map = new Map<string, StartupGeneratorParameters>();
    for (const entry of availableEntries) {
      map.set(entry.id, entry);
    }
    return map;
  }, [availableEntries]);

  const addToScenario = useAddGeneratorToScenarioMutation();

  function handleAdd(entry: StartupGeneratorParameters) {
    addToScenario.mutate(
      { name: scenarioName, generatorId: entry.id },
      {
        onSuccess: () => {
          showSuccessNotification('Success', 'Instance added to scenario');
          modals.closeAll();
        },
        onError: (addError) => {
          showErrorNotification('Failed to add instance', addError);
        },
      },
    );
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
          icon={<Box c="red" component={IconAlertSquareRounded} />}
          title="Failed to load instances"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isSuccess) {
    return (
      <AddInstanceForm
        availableEntries={availableEntries}
        entryMap={entryMap}
        isPending={addToScenario.isPending}
        onAdd={handleAdd}
      />
    );
  }

  return null;
};
