import {
  Anchor,
  Badge,
  Button,
  Code,
  Divider,
  Group,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconExternalLink } from '@tabler/icons-react';
import bytes from 'bytes';
import { FC } from 'react';

import { buildEntryUrl } from './entry-url';
import {
  Catalog,
  CatalogEntry,
  ConnectedRepository,
} from '@/api/routes/repositories/schemas';

interface GeneratorDetailsModalProps {
  repository: ConnectedRepository;
  catalog: Catalog;
  entry: CatalogEntry;
  onInstall: () => void;
}

const Fact: FC<{ label: string; children: React.ReactNode }> = ({
  label,
  children,
}) => (
  <Group gap="sm" wrap="nowrap" align="start">
    <Text size="sm" c="dimmed" w={130} style={{ flexShrink: 0 }}>
      {label}
    </Text>
    <Text size="sm" component="div">
      {children}
    </Text>
  </Group>
);

/**
 * Everything the repository states about one published generator,
 * gathered in one place so a decision to install it is made without
 * reading the table sideways.
 */
export const GeneratorDetailsModal: FC<GeneratorDetailsModalProps> = ({
  repository,
  catalog,
  entry,
  onInstall,
}) => {
  const sourceUrl = buildEntryUrl(repository.url, repository.ref, entry.path);

  return (
    <Stack>
      <Stack gap={4}>
        <Text fw={600}>{entry.title ?? entry.name}</Text>
        <Text size="sm" c="dimmed">
          {entry.summary ?? 'The generator carries no description.'}
        </Text>
      </Stack>

      <Divider />

      <Stack gap="xs">
        <Fact label="Generator">
          <Code>{entry.name}</Code>
        </Fact>
        <Fact label="Content">
          {bytes(entry.size)} in {entry.file_count}{' '}
          {entry.file_count === 1 ? 'file' : 'files'}
        </Fact>
        <Fact label="Repository">{repository.name}</Fact>
        <Fact label="Branch or tag">{repository.ref ?? 'default branch'}</Fact>
        <Fact label="Path">
          {sourceUrl === null ? (
            <Code>{entry.path}</Code>
          ) : (
            <Anchor href={sourceUrl} target="_blank" size="sm">
              <Group gap={4} wrap="nowrap" component="span">
                {entry.path}
                <IconExternalLink size={14} />
              </Group>
            </Anchor>
          )}
        </Fact>
        <Fact label="Revision">
          <Code>{catalog.revision.slice(0, 7)}</Code>
          {catalog.author ? ` by ${catalog.author}` : ''},{' '}
          {new Date(catalog.committed_at).toLocaleDateString()}
        </Fact>
        {entry.installed_as.length > 0 && (
          <Fact label="Installed as">
            <Stack gap={4}>
              {entry.installed_as.map((installed) => (
                <Group key={installed.project} gap="xs">
                  <Text size="sm">{installed.project}</Text>
                  <Badge
                    size="xs"
                    variant="light"
                    color={installed.outdated ? 'yellow' : 'green'}
                  >
                    {installed.outdated ? 'outdated' : 'up to date'}
                  </Badge>
                  <Text size="xs" c="dimmed">
                    {new Date(installed.installed_at).toLocaleDateString()}
                  </Text>
                </Group>
              ))}
            </Stack>
          </Fact>
        )}
      </Stack>

      <Group justify="end">
        <Button variant="default" onClick={() => modals.closeAll()}>
          Close
        </Button>
        <Button onClick={onInstall}>
          {entry.installed_as.length > 0 ? 'Install again' : 'Install'}
        </Button>
      </Group>
    </Stack>
  );
};
