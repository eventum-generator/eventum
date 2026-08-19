import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Center,
  Code,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconSearch, IconStar, IconX } from '@tabler/icons-react';
import { FC, useState } from 'react';

import { useDiscoveredRepositories } from '@/api/hooks/useRepositories';
import { DiscoveredRepository } from '@/api/routes/repositories/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

/** Page describing what a repository does to appear in this list. */
const PUBLISHING_DOCS_URL =
  'https://eventum.run/docs/studio/repositories#publishing-your-own-repository';

/** Waited out before searching, so typing a word does not spend a
 *  search on every letter of it. */
const TYPING_PAUSE = 400;

interface DiscoverRepositoriesProps {
  /** Opens the connect dialog for a repository of this list. */
  onConnect: (repository: DiscoveredRepository) => void;
}

const Marks: FC<{ repository: DiscoveredRepository }> = ({ repository }) => (
  <>
    {repository.official && (
      <Badge variant="light" size="sm">
        official
      </Badge>
    )}
    {repository.connected && (
      <Badge variant="light" color="green" size="sm">
        connected
      </Badge>
    )}
    {repository.archived && (
      <Badge variant="default" size="sm">
        archived
      </Badge>
    )}
  </>
);

const RepositoryCard: FC<{
  repository: DiscoveredRepository;
  onConnect: () => void;
}> = ({ repository, onConnect }) => (
  <Paper withBorder p="md">
    <Group justify="space-between" align="flex-start" wrap="nowrap" gap="lg">
      <Stack gap={6} style={{ minWidth: 0 }}>
        <Group gap="xs">
          <Anchor
            href={repository.page_url}
            target="_blank"
            rel="noreferrer noopener"
            fw={600}
            size="sm"
          >
            {repository.full_name}
          </Anchor>
          <Marks repository={repository} />
        </Group>

        <Text size="sm" c="dimmed" lineClamp={2}>
          {repository.description ?? 'No description'}
        </Text>

        <Group gap="md">
          <Group gap={4}>
            <IconStar size={14} stroke={1.5} />
            <Text size="xs" c="dimmed">
              {repository.stars}
            </Text>
          </Group>
          {repository.license !== null && (
            <Text size="xs" c="dimmed">
              {repository.license}
            </Text>
          )}
          {repository.updated_at !== null && (
            <Text size="xs" c="dimmed">
              Updated {new Date(repository.updated_at).toLocaleDateString()}
            </Text>
          )}
        </Group>
      </Stack>

      <Button
        variant="default"
        disabled={repository.connected}
        onClick={onConnect}
      >
        {repository.connected ? 'Connected' : 'Connect'}
      </Button>
    </Group>
  </Paper>
);

/**
 * Repositories that publish generators in the open.
 *
 * A repository appears here by carrying the topic the answer names, so
 * the list is what its authors published about themselves and is not
 * reviewed - which the page states rather than implies.
 */
export const DiscoverRepositories: FC<DiscoverRepositoriesProps> = ({
  onConnect,
}) => {
  const [query, setQuery] = useState('');
  const [searched] = useDebouncedValue(query, TYPING_PAUSE);

  const {
    data: discovery,
    isLoading,
    isError,
    error,
  } = useDiscoveredRepositories(searched.trim(), true);

  return (
    <Stack>
      <Alert
        variant="default"
        icon={<AlertIcon variant="warn" />}
        title="Community repositories are not reviewed"
      >
        Any repository carrying the topic is listed here, and its content is not
        reviewed by Eventum. A generator can carry templates and scripts that
        are executed on this machine when the generator runs, so review what you
        install and connect only repositories you trust.
      </Alert>

      <Group justify="space-between" align="center">
        <TextInput
          w={320}
          placeholder="Search published repositories"
          leftSection={<IconSearch size={16} />}
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
          rightSection={
            query ? (
              <ActionIcon
                variant="subtle"
                color="gray"
                aria-label="Clear search"
                onClick={() => setQuery('')}
              >
                <IconX size={16} />
              </ActionIcon>
            ) : null
          }
        />
        {discovery !== undefined && (
          <Text size="sm" c="dimmed">
            {discovery.total_count}{' '}
            {discovery.total_count === 1 ? 'repository' : 'repositories'} found
          </Text>
        )}
      </Group>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to search published repositories"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
        </Alert>
      )}

      {discovery?.entries.length === 0 && (
        <Paper withBorder p="xl">
          <Stack align="center" gap="xs" py="lg">
            <Text fw={600}>Nothing published matches</Text>
            <Text size="sm" c="dimmed" ta="center" maw={480}>
              {discovery.query
                ? 'No repository carrying the topic matches these words.'
                : 'No repository carries the topic yet.'}
            </Text>
          </Stack>
        </Paper>
      )}

      {discovery?.entries.map((repository) => (
        <RepositoryCard
          key={repository.full_name}
          repository={repository}
          onConnect={() => onConnect(repository)}
        />
      ))}

      {discovery !== undefined && (
        <Text size="xs" c="dimmed">
          A repository is listed here by carrying the{' '}
          <Code>{discovery.topic}</Code> topic on GitHub.{' '}
          <Anchor
            href={PUBLISHING_DOCS_URL}
            target="_blank"
            rel="noreferrer noopener"
            size="xs"
          >
            Publish your own
          </Anchor>
        </Text>
      )}
    </Stack>
  );
};
