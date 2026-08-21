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
        onSuccess: (updated) => {
          const carried = [...updated.projects, ...updated.repositories];

          showSuccessNotification(
            'Renamed',
            carried.length > 0
              ? `Secret "${secretName}" renamed to "${newName}", ` +
                  `${carried.join(', ')} updated`
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
            <Code>{`\${secrets.${secretName}}`}</Code>. The placeholder is
            rewritten in each of them; one already running keeps the
            configuration it loaded and reads the new name when it starts again.
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
