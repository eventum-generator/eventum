import {
  Accordion,
  ActionIcon,
  Center,
  Group,
  Text,
  Tooltip,
} from '@mantine/core';
import { IconRefresh, IconTrash } from '@tabler/icons-react';
import { FC, useEffect, useRef } from 'react';

import { RepositoryCatalog } from './RepositoryCatalog';
import { RepositoryStatusBadge } from './RepositoryStatusBadge';
import {
  useCheckRepositoryMutation,
  useRefreshCatalogMutation,
} from '@/api/hooks/useRepositories';
import { ConnectedRepository } from '@/api/routes/repositories/schemas';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RepositoryRowProps {
  repository: ConnectedRepository;
  existingProjectNames: string[];
  isOpened: boolean;
  onDisconnect: () => void;
}

/**
 * One connected repository: what it is, whether it answers, and what
 * it publishes.
 *
 * Each row owns its own mutations. A mutation carries the callbacks of
 * its last call, so one shared between rows would report the outcome
 * of whichever row acted last and lose the rest.
 */
export const RepositoryRow: FC<RepositoryRowProps> = ({
  repository,
  existingProjectNames,
  isOpened,
  onDisconnect,
}) => {
  const refreshCatalog = useRefreshCatalogMutation();
  const checkRepository = useCheckRepositoryMutation();

  // A status is what the instance found when it last asked, and it
  // knows nothing until it does - so a repository not checked in this
  // process is checked once, when the page opens.
  const isChecked = useRef(false);
  const { name, status } = repository;
  const checkMutate = checkRepository.mutate;

  useEffect(() => {
    if (status.state !== 'unknown' || isChecked.current) return;

    isChecked.current = true;
    checkMutate(name);
  }, [name, status.state, checkMutate]);

  const handleRefresh = () =>
    refreshCatalog.mutate(name, {
      onSuccess: (catalog) =>
        showSuccessNotification(
          'Refreshed',
          `Repository "${name}" publishes ${catalog.entries.length} ` +
            `${catalog.entries.length === 1 ? 'generator' : 'generators'}`
        ),
      onError: (error) =>
        showErrorNotification('Failed to refresh repository', error),
    });

  return (
    <Accordion.Item value={name}>
      <Center>
        <Accordion.Control>
          <Group gap="xs" wrap="nowrap">
            <Text size="sm" fw={600}>
              {name}
            </Text>
            <RepositoryStatusBadge
              status={status}
              isChecking={checkRepository.isPending}
            />
          </Group>
          <Text size="xs" c="dimmed">
            {repository.url}
            {repository.ref ? ` · ${repository.ref}` : ''}
          </Text>
        </Accordion.Control>
        <Group gap="xs" pr="md" wrap="nowrap">
          <Tooltip label="Refresh catalog">
            <ActionIcon
              variant="subtle"
              // The icon carries the text colour rather than the dimmed
              // grey a control defaults to: it sits beside the red of
              // disconnecting, where a dimmed glyph reads as disabled.
              c="var(--mantine-color-text)"
              aria-label="Refresh catalog"
              loading={refreshCatalog.isPending}
              onClick={handleRefresh}
            >
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Disconnect">
            <ActionIcon
              variant="subtle"
              color="red"
              aria-label="Disconnect repository"
              onClick={onDisconnect}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Center>
      <Accordion.Panel>
        <RepositoryCatalog
          repository={repository}
          existingProjectNames={existingProjectNames}
          enabled={isOpened}
        />
      </Accordion.Panel>
    </Accordion.Item>
  );
};
