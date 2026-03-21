import {
  Alert,
  Box,
  Center,
  Container,
  Loader,
  Select,
  Stack,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FC, useMemo } from 'react';

import { useStartupGenerators } from '@/api/hooks/useStartup';
import { updateGeneratorInStartup } from '@/api/routes/startup';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

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
      <Stack>
        <Select
          label="Instance"
          data={availableEntries.map((e) => e.id)}
          searchable
          nothingFoundMessage="No instances available"
          placeholder="Select instance"
          onChange={(value) => {
            if (!value) return;
            const entry = entryMap.get(value);
            if (entry) addToScenario.mutate({ entry });
          }}
          disabled={addToScenario.isPending || availableEntries.length === 0}
        />
      </Stack>
    );
  }

  return null;
};
