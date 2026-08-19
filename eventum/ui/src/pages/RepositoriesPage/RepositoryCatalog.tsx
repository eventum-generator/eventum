import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconSearch, IconX } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC, useMemo, useState } from 'react';

import { GeneratorDetailsModal } from './GeneratorDetailsModal';
import { InstallGeneratorModal } from './InstallGeneratorModal';
import { useRepositoryCatalog } from '@/api/hooks/useRepositories';
import {
  CatalogEntry,
  ConnectedRepository,
} from '@/api/routes/repositories/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface RepositoryCatalogProps {
  repository: ConnectedRepository;
  existingProjectNames: string[];
  enabled: boolean;
}

function matches(entry: CatalogEntry, query: string): boolean {
  const haystack = [entry.name, entry.title ?? '', entry.summary ?? '']
    .join(' ')
    .toLowerCase();

  return haystack.includes(query.trim().toLowerCase());
}

/**
 * Generators one repository publishes. The catalog is read when the
 * repository is opened, since reading it makes the instance fetch the
 * repository.
 */
export const RepositoryCatalog: FC<RepositoryCatalogProps> = ({
  repository,
  existingProjectNames,
  enabled,
}) => {
  const [query, setQuery] = useState('');

  const {
    data: catalog,
    isLoading,
    isError,
    error,
  } = useRepositoryCatalog(repository.name, enabled);

  const entries = useMemo(
    () => (catalog?.entries ?? []).filter((entry) => matches(entry, query)),
    [catalog, query]
  );

  if (isLoading) {
    return (
      <Center py="lg">
        <Loader size="sm" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Alert
        variant="default"
        icon={<AlertIcon variant="error" />}
        title="Failed to read the catalog"
      >
        {error.message}
        <ShowErrorDetailsAnchor error={error} prependDot />
      </Alert>
    );
  }

  if (catalog === undefined) {
    return <></>;
  }

  if (catalog.entries.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        The repository publishes no generators.
      </Text>
    );
  }

  const openInstallModal = (entry: CatalogEntry) =>
    modals.open({
      title: 'Install generator',
      children: (
        <InstallGeneratorModal
          repositoryName={repository.name}
          entry={entry}
          existingProjectNames={existingProjectNames}
        />
      ),
      size: 'lg',
    });

  const openDetailsModal = (entry: CatalogEntry) =>
    modals.open({
      title: 'Generator',
      children: (
        <GeneratorDetailsModal
          repository={repository}
          catalog={catalog}
          entry={entry}
          onInstall={() => {
            modals.closeAll();
            openInstallModal(entry);
          }}
        />
      ),
      size: 'lg',
    });

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="center">
        <Text size="xs" c="dimmed">
          {catalog.entries.length}{' '}
          {catalog.entries.length === 1 ? 'generator' : 'generators'}
          {entries.length !== catalog.entries.length
            ? ` · ${entries.length} shown`
            : ''}{' '}
          · revision {catalog.revision.slice(0, 7)}
          {catalog.author ? ` by ${catalog.author}` : ''} · read{' '}
          {new Date(catalog.refreshed_at).toLocaleString()}
        </Text>
        <TextInput
          size="xs"
          leftSection={<IconSearch size={14} />}
          rightSection={
            query ? (
              <ActionIcon
                variant="transparent"
                onClick={() => setQuery('')}
                data-input-section
              >
                <IconX size={14} />
              </ActionIcon>
            ) : null
          }
          placeholder="search generators..."
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
          w={260}
        />
      </Group>

      {entries.length === 0 ? (
        <Text size="sm" c="dimmed" py="md">
          No generator matches &quot;{query}&quot;.
        </Text>
      ) : (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w="30%">Generator</Table.Th>
              <Table.Th>Summary</Table.Th>
              <Table.Th style={{ whiteSpace: 'nowrap' }}>Size</Table.Th>
              <Table.Th
                style={{
                  width: '1%',
                  whiteSpace: 'nowrap',
                  textAlign: 'right',
                }}
              >
                Actions
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {entries.map((entry) => (
              <Table.Tr
                key={entry.name}
                onClick={() => openDetailsModal(entry)}
                style={{ cursor: 'pointer' }}
              >
                <Table.Td>
                  <Group gap="xs" wrap="nowrap">
                    <Text size="sm" fw={600}>
                      {entry.title ?? entry.name}
                    </Text>
                    {entry.installed_as.length > 0 && (
                      <Badge
                        size="xs"
                        variant="light"
                        color={
                          entry.installed_as.some((item) => item.outdated)
                            ? 'yellow'
                            : 'green'
                        }
                      >
                        {entry.installed_as.some((item) => item.outdated)
                          ? 'update available'
                          : 'installed'}
                      </Badge>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    {entry.name}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">
                    {entry.summary ?? '-'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                    {bytes(entry.size)} · {entry.file_count}{' '}
                    {entry.file_count === 1 ? 'file' : 'files'}
                  </Text>
                </Table.Td>
                <Table.Td style={{ textAlign: 'right' }}>
                  <Button
                    variant="default"
                    size="compact-sm"
                    onClick={(event) => {
                      event.stopPropagation();
                      openInstallModal(entry);
                    }}
                  >
                    Install
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
};
