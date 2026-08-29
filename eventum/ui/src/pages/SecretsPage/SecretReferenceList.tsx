import { Alert, List, Loader, Stack, Text } from '@mantine/core';
import { FC, ReactNode } from 'react';

import { useSecretReferences } from '@/api/hooks/useSecrets';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface SecretReferenceListProps {
  secretName: string;
  /** Rendered above the two lists, when anything refers to the secret. */
  lead?: ReactNode;
  /** What the projects reading the secret are about to face. */
  projectsNote: ReactNode;
  /** What the repositories authenticating with it are about to face. */
  repositoriesNote: ReactNode;
  /** Shown when nothing refers to the secret. */
  noneNote: ReactNode;
}

const NameList: FC<{ names: string[] }> = ({ names }) => (
  <List size="sm" mt="xs" fw={600}>
    {names.map((name) => (
      <List.Item key={name}>{name}</List.Item>
    ))}
  </List>
);

/**
 * What refers to a secret, told apart by kind.
 *
 * The two kinds face different consequences from whatever the caller
 * is about to do, so each carries its own note. Until the answer is
 * in, and when it cannot be had at all, nothing is claimed about the
 * secret - saying that nothing refers to it is the one answer this
 * must never give on a guess.
 */
export const SecretReferenceList: FC<SecretReferenceListProps> = ({
  secretName,
  lead,
  projectsNote,
  repositoriesNote,
  noneNote,
}) => {
  const {
    data: references,
    isError,
    error,
  } = useSecretReferences(secretName, true);

  if (isError) {
    return (
      <Alert
        variant="default"
        icon={<AlertIcon variant="warn" />}
        title="Cannot tell what uses this secret"
      >
        {error?.message}
        {error && <ShowErrorDetailsAnchor error={error} prependDot />}
      </Alert>
    );
  }

  if (references === undefined) {
    return <Loader size="xs" />;
  }

  const { projects, repositories } = references;

  if (projects.length === 0 && repositories.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        {noneNote}
      </Text>
    );
  }

  return (
    <Stack gap="sm">
      {lead}

      {projects.length > 0 && (
        <Text size="sm">
          {projectsNote}
          <NameList names={projects} />
        </Text>
      )}

      {repositories.length > 0 && (
        <Text size="sm">
          {repositoriesNote}
          <NameList names={repositories} />
        </Text>
      )}
    </Stack>
  );
};
