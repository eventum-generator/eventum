import { Code, List, Loader, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import {
  useRenameSecretMutation,
  useSecretReferences,
} from '@/api/hooks/useSecrets';
import {
  SECRET_NAME_ERROR,
  SECRET_NAME_PATTERN,
} from '@/api/routes/secrets/schemas';
import { RenameModal } from '@/components/modals/RenameModal';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RenameSecretModalProps {
  secretName: string;
  existingSecretNames: string[];
}

export const RenameSecretModal: FC<RenameSecretModalProps> = ({
  secretName,
  existingSecretNames,
}) => {
  const renameSecret = useRenameSecretMutation();
  const { data: references, isLoading: isReferencesLoading } =
    useSecretReferences(secretName, true);

  function handleRename(newName: string) {
    renameSecret.mutate(
      { name: secretName, newName },
      {
        onSuccess: () => {
          showSuccessNotification(
            'Renamed',
            `Secret "${secretName}" renamed to "${newName}"`
          );
          modals.closeAll();
        },
        onError: (error) =>
          showErrorNotification('Failed to rename secret', error),
      }
    );
  }

  return (
    <RenameModal
      label="New secret name"
      currentName={secretName}
      takenNames={existingSecretNames}
      pattern={SECRET_NAME_PATTERN}
      patternError={SECRET_NAME_ERROR}
      isPending={renameSecret.isPending}
      onRename={handleRename}
    >
      {isReferencesLoading ? (
        <Loader size="xs" />
      ) : references && references.length > 0 ? (
        <Text size="sm">
          These projects read the secret as{' '}
          <Code>{`\${secrets.${secretName}}`}</Code>. Update the placeholder in
          each of them after renaming - it is not rewritten automatically.
          <List size="sm" mt="xs" fw={600}>
            {references.map((name) => (
              <List.Item key={name}>{name}</List.Item>
            ))}
          </List>
        </Text>
      ) : (
        <Text size="sm" c="dimmed">
          No project configuration reads this secret.
        </Text>
      )}
    </RenameModal>
  );
};
