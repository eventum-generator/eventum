import { Alert, Code, List, Loader, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import {
  useRenameSecretMutation,
  useSecretReferences,
} from '@/api/hooks/useSecrets';
import { RenameModal } from '@/components/modals/RenameModal';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RenameSecretModalProps {
  secretName: string;
  existingSecretNames: string[];
}

const NameList: FC<{ names: string[] }> = ({ names }) => (
  <List size="sm" mt="xs" fw={600}>
    {names.map((name) => (
      <List.Item key={name}>{name}</List.Item>
    ))}
  </List>
);

export const RenameSecretModal: FC<RenameSecretModalProps> = ({
  secretName,
  existingSecretNames,
}) => {
  const renameSecret = useRenameSecretMutation();
  const {
    data: references,
    isError: isReferencesError,
    error: referencesError,
  } = useSecretReferences(secretName, true);

  function handleRename(newName: string) {
    renameSecret.mutate(
      { name: secretName, newName },
      {
        onSuccess: (repointed) => {
          showSuccessNotification(
            'Renamed',
            repointed.length > 0
              ? `Secret "${secretName}" renamed to "${newName}", ` +
                  `${repointed.join(', ')} repointed at it`
              : `Secret "${secretName}" renamed to "${newName}"`
          );
          modals.closeAll();
        },
        onError: (error) =>
          showErrorNotification('Failed to rename secret', error),
      }
    );
  }

  const projects = references?.projects ?? [];
  const repositories = references?.repositories ?? [];
  const isReferenced = projects.length > 0 || repositories.length > 0;

  return (
    <RenameModal
      label="New secret name"
      currentName={secretName}
      takenNames={existingSecretNames}
      isPending={renameSecret.isPending}
      onRename={handleRename}
    >
      {isReferencesError ? (
        <Alert
          variant="default"
          icon={<AlertIcon variant="warn" />}
          title="Cannot tell what uses this secret"
        >
          {referencesError?.message}
          {referencesError && (
            <ShowErrorDetailsAnchor error={referencesError} prependDot />
          )}
        </Alert>
      ) : references === undefined ? (
        // Until the answer is in, nothing is known about the secret -
        // saying that nothing reads it is the very claim this dialog
        // must not make on a guess.
        <Loader size="xs" />
      ) : isReferenced ? (
        <Stack gap="sm">
          {projects.length > 0 && (
            <Text size="sm">
              These projects read the secret as{' '}
              <Code>{`\${secrets.${secretName}}`}</Code>. Update the placeholder
              in each of them after renaming - it is not rewritten
              automatically.
              <NameList names={projects} />
            </Text>
          )}

          {repositories.length > 0 && (
            <Text size="sm">
              These connected repositories authenticate with the secret and are
              repointed at the new name.
              <NameList names={repositories} />
            </Text>
          )}
        </Stack>
      ) : (
        <Text size="sm" c="dimmed">
          Nothing reads this secret.
        </Text>
      )}
    </RenameModal>
  );
};
