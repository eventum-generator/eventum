import {
  Alert,
  Box,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded, IconSearch } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { useStartupGenerators } from '@/api/hooks/useStartup';
import { updateGeneratorInStartup } from '@/api/routes/startup';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface AddGeneratorModalProps {
  scenarioName: string;
}

export const AddGeneratorModal = ({ scenarioName }: AddGeneratorModalProps) => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');

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

  const filteredEntries = useMemo(() => {
    if (!search.trim()) return availableEntries;

    const lowerSearch = search.toLowerCase();
    return availableEntries.filter(
      (entry) =>
        entry.id.toLowerCase().includes(lowerSearch) ||
        entry.path.toLowerCase().includes(lowerSearch)
    );
  }, [availableEntries, search]);

  const addToScenario = useMutation({
    mutationFn: async ({
      entry,
    }: {
      entry: StartupGeneratorParameters;
    }) => {
      const updatedScenarios = [...(entry.scenarios ?? []), scenarioName];
      await updateGeneratorInStartup(entry.id, {
        ...entry,
        scenarios: updatedScenarios,
      });
    },
    onSuccess: async (_, { entry }) => {
      await queryClient.invalidateQueries({ queryKey: ['startup'] });
      await queryClient.invalidateQueries({
        queryKey: ['globals-usage', entry.id],
      });
      notifications.show({
        title: 'Success',
        message: `Added "${entry.id}" to scenario`,
        color: 'green',
      });
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: (
          <>
            Failed to add generator to scenario
            <ShowErrorDetailsAnchor error={error} prependDot />
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
      <Stack>
        <TextInput
          leftSection={<IconSearch size={16} />}
          placeholder="Search generators..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        {availableEntries.length === 0 ? (
          <Text size="sm" c="dimmed" ta="center">
            All generators are already in this scenario.
          </Text>
        ) : filteredEntries.length === 0 ? (
          <Text size="sm" c="dimmed" ta="center">
            No generators match your search.
          </Text>
        ) : (
          <Stack gap="xs" mah={400} style={{ overflowY: 'auto' }}>
            {filteredEntries.map((entry) => {
              const isAdding =
                addToScenario.isPending &&
                addToScenario.variables?.entry.id === entry.id;

              return (
                <Group key={entry.id} justify="space-between" wrap="nowrap">
                  <Stack gap={0} style={{ minWidth: 0 }}>
                    <Text size="sm" fw={500} truncate>
                      {entry.id}
                    </Text>
                    <Text size="xs" c="dimmed" truncate>
                      {entry.path}
                    </Text>
                  </Stack>
                  <Button
                    size="xs"
                    variant="light"
                    loading={isAdding}
                    onClick={() => addToScenario.mutate({ entry })}
                  >
                    Add
                  </Button>
                </Group>
              );
            })}
          </Stack>
        )}
      </Stack>
    );
  }

  return null;
};
