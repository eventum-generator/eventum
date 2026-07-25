import { Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import { useRenameGeneratorMutation } from '@/api/hooks/useGenerators';
import { RenameModal } from '@/components/modals/RenameModal';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RenameInstanceModalProps {
  instanceId: string;
  existingInstanceIds: string[];
}

export const RenameInstanceModal: FC<RenameInstanceModalProps> = ({
  instanceId,
  existingInstanceIds,
}) => {
  const renameInstance = useRenameGeneratorMutation();

  function handleRename(newId: string) {
    renameInstance.mutate(
      { id: instanceId, newId },
      {
        onSuccess: () => {
          showSuccessNotification(
            'Renamed',
            `Instance "${instanceId}" renamed to "${newId}"`
          );
          modals.closeAll();
        },
        onError: (error) =>
          showErrorNotification('Failed to rename instance', error),
      }
    );
  }

  return (
    <RenameModal
      label="New instance name"
      currentName={instanceId}
      takenNames={existingInstanceIds}
      isPending={renameInstance.isPending}
      onRename={handleRename}
    >
      <Text size="sm" c="dimmed">
        Scenario membership and all parameters are kept. Logs written under the
        old name stay in their own file.
      </Text>
    </RenameModal>
  );
};
