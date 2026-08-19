import {
  Accordion,
  ActionIcon,
  Alert,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconPlus, IconRefresh, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';

import { AddRepositoryModal } from './AddRepositoryModal';
import { RepositoriesEmptyState } from './RepositoriesEmptyState';
import { RepositoryCatalog } from './RepositoryCatalog';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import {
  useDeleteRepositoryMutation,
  useRefreshCatalogMutation,
  useRepositories,
} from '@/api/hooks/useRepositories';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

export default function RepositoriesPage() {
  const [openedRepository, setOpenedRepository] = useState<string | null>(null);

  const {
    data: repositories,
    isLoading,
    isError,
    error,
    isSuccess,
  } = useRepositories();
  const { data: generatorDirs } = useGeneratorDirs(false);

  const deleteRepository = useDeleteRepositoryMutation();
  const refreshCatalog = useRefreshCatalogMutation();

  if (isLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container size="md" mt="lg">
        <PageTitle title="Repositories" />
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to load connected repositories"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </Alert>
      </Container>
    );
  }

  if (!isSuccess) {
    return <></>;
  }

  const existingProjectNames = generatorDirs ?? [];

  const openAddModal = () =>
    modals.open({
      title: 'Connect repository',
      children: (
        <AddRepositoryModal
          existingNames={repositories.map((item) => item.name)}
        />
      ),
      size: 'lg',
    });

  const handleRefresh = (name: string) =>
    refreshCatalog.mutate(name, {
      onSuccess: (catalog) =>
        showSuccessNotification(
          'Refreshed',
          `Repository "${name}" publishes ${catalog.entries.length} ` +
            `${catalog.entries.length === 1 ? 'generator' : 'generators'}`
        ),
      onError: (mutationError) =>
        showErrorNotification('Failed to refresh repository', mutationError),
    });

  const handleDisconnect = (name: string) =>
    modals.openConfirmModal({
      title: 'Disconnect repository',
      children: (
        <Text size="sm">
          Repository &quot;{name}&quot; will no longer be listed. Generators
          already installed from it stay in the workspace.
        </Text>
      ),
      labels: { confirm: 'Disconnect', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () =>
        deleteRepository.mutate(name, {
          onSuccess: () =>
            showSuccessNotification(
              'Disconnected',
              `Repository "${name}" is disconnected`
            ),
          onError: (mutationError) =>
            showErrorNotification(
              'Failed to disconnect repository',
              mutationError
            ),
        }),
    });

  const total = repositories.length;

  if (total === 0) {
    return (
      <Container size="100%">
        <Stack>
          <PageTitle title="Repositories" />
          <RepositoriesEmptyState onConnect={openAddModal} />
        </Stack>
      </Container>
    );
  }

  return (
    <Container size="100%">
      <Stack>
        <Group align="baseline" gap="sm">
          <PageTitle title="Repositories" />
          <Text size="sm" c="dimmed">
            {total} {total === 1 ? 'repository' : 'repositories'}
          </Text>
        </Group>

        <Paper withBorder p="sm">
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Open a repository to read what it publishes and install a
              generator as a project.
            </Text>
            <Button leftSection={<IconPlus size={16} />} onClick={openAddModal}>
              Connect
            </Button>
          </Group>
        </Paper>

        <Accordion
          variant="separated"
          value={openedRepository}
          onChange={setOpenedRepository}
        >
          {repositories.map((repository) => (
            <Accordion.Item key={repository.name} value={repository.name}>
              <Center>
                <Accordion.Control>
                  <Text size="sm" fw={600}>
                    {repository.name}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {repository.url}
                    {repository.ref ? ` · ${repository.ref}` : ''}
                  </Text>
                </Accordion.Control>
                <Group gap="xs" pr="md" wrap="nowrap">
                  <Tooltip label="Refresh catalog">
                    <ActionIcon
                      variant="subtle"
                      loading={
                        refreshCatalog.isPending &&
                        refreshCatalog.variables === repository.name
                      }
                      onClick={() => handleRefresh(repository.name)}
                    >
                      <IconRefresh size={16} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Disconnect">
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      onClick={() => handleDisconnect(repository.name)}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Center>
              <Accordion.Panel>
                <RepositoryCatalog
                  repositoryName={repository.name}
                  existingProjectNames={existingProjectNames}
                  enabled={openedRepository === repository.name}
                />
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion>
      </Stack>
    </Container>
  );
}
