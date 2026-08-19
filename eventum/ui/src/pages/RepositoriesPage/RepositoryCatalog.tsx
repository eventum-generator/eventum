import {
  Alert,
  Button,
  Center,
  Loader,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import bytes from 'bytes';
import { FC } from 'react';

import { InstallGeneratorModal } from './InstallGeneratorModal';
import { useRepositoryCatalog } from '@/api/hooks/useRepositories';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface RepositoryCatalogProps {
  repositoryName: string;
  existingProjectNames: string[];
  enabled: boolean;
}

/**
 * Generators one repository publishes. The catalog is read when the
 * repository is opened, since reading it makes the instance fetch the
 * repository.
 */
export const RepositoryCatalog: FC<RepositoryCatalogProps> = ({
  repositoryName,
  existingProjectNames,
  enabled,
}) => {
  const {
    data: catalog,
    isLoading,
    isError,
    error,
  } = useRepositoryCatalog(repositoryName, enabled);

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

  const openInstallModal = (entryName: string) => {
    const entry = catalog.entries.find((item) => item.name === entryName);

    if (entry === undefined) return;

    modals.open({
      title: 'Install generator',
      children: (
        <InstallGeneratorModal
          repositoryName={repositoryName}
          entry={entry}
          existingProjectNames={existingProjectNames}
        />
      ),
      size: 'lg',
    });
  };

  return (
    <Stack gap="sm">
      <Text size="xs" c="dimmed">
        Revision {catalog.revision.slice(0, 7)} · read{' '}
        {new Date(catalog.refreshed_at).toLocaleString()}
      </Text>

      <Table>
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
          {catalog.entries.map((entry) => (
            <Table.Tr key={entry.name}>
              <Table.Td>
                <Text size="sm" fw={600}>
                  {entry.title ?? entry.name}
                </Text>
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
                  onClick={() => openInstallModal(entry.name)}
                >
                  Install
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
};
