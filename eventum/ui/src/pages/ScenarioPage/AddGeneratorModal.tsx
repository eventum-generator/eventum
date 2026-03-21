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
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FC, useMemo, useState } from 'react';

import { useStartupGenerators } from '@/api/hooks/useStartup';
import { updateGeneratorInStartup } from '@/api/routes/startup';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

function AddInstanceForm({
  availableEntries,
  entryMap,
  isPending,
  onAdd,
}: {
  availableEntries: StartupGeneratorParameters[];
  entryMap: Map<string, StartupGeneratorParameters>;
  isPending: boolean;
  onAdd: (entry: StartupGeneratorParameters) => void;
}) {
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
  const queryClient = useQueryClient();

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

  const addToScenario = useMutation({
    mutationFn: async ({ entry }: { entry: StartupGeneratorParameters }) => {
      const updatedScenarios = [...(entry.scenarios ?? []), scenarioName];
      await updateGeneratorInStartup(entry.id, {
        ...entry,
        scenarios: updatedScenarios,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['startup'] });
      notifications.show({
        title: 'Success',
        message: 'Instance added to scenario',
        color: 'green',
      });
      modals.closeAll();
    },
    onError: (addError) => {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to add instance
            <ShowErrorDetailsAnchor error={addError} prependDot />
          </>
        ),
        color: 'red',
      });
    },
  });

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
        onAdd={(entry) => addToScenario.mutate({ entry })}
      />
    );
  }

  return null;
};
