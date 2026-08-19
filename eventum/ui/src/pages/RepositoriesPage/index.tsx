import {
  Accordion,
  Alert,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AddRepositoryModal } from './AddRepositoryModal';
import { RepositoriesEmptyState } from './RepositoriesEmptyState';
import { RepositoryRow } from './RepositoryRow';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import {
  useDeleteRepositoryMutation,
  useRepositories,
} from '@/api/hooks/useRepositories';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

export default function RepositoriesPage() {
  const navigate = useNavigate();
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
          onOpenSecrets={() => void navigate(ROUTE_PATHS.SECRETS)}
        />
      ),
      size: 'lg',
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
          onSuccess: () => {
            // The panel of a repository that is gone must not stay
            // open: a repository connected under that name again
            // would be fetched without anyone asking for it.
            setOpenedRepository((current) =>
              current === name ? null : current
            );
            showSuccessNotification(
              'Disconnected',
              `Repository "${name}" is disconnected`
            );
          },
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
            <RepositoryRow
              key={repository.name}
              repository={repository}
              existingProjectNames={existingProjectNames}
              isOpened={openedRepository === repository.name}
              onDisconnect={() => handleDisconnect(repository.name)}
            />
          ))}
        </Accordion>
      </Stack>
    </Container>
  );
}
