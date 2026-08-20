import { Code } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import { SecretReferenceList } from './SecretReferenceList';
import { useRenameSecretMutation } from '@/api/hooks/useSecrets';
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

  return (
    <RenameModal
      label="New secret name"
      currentName={secretName}
      takenNames={existingSecretNames}
      isPending={renameSecret.isPending}
      onRename={handleRename}
    >
      <SecretReferenceList
        secretName={secretName}
        projectsNote={
          <>
            These projects read the secret as{' '}
            <Code>{`\${secrets.${secretName}}`}</Code>. Update the placeholder
            in each of them after renaming - it is not rewritten automatically.
          </>
        }
        repositoriesNote={
          <>
            These connected repositories authenticate with the secret and are
            repointed at the new name.
          </>
        }
        noneNote="Nothing reads this secret."
      />
    </RenameModal>
  );
};
