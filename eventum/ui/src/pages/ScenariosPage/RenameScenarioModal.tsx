import { Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import { useRenameScenarioMutation } from '@/api/hooks/useScenarios';
import { RenameModal } from '@/components/modals/RenameModal';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RenameScenarioModalProps {
  scenarioName: string;
  existingScenarioNames: string[];
  instanceCount: number;
}

export const RenameScenarioModal: FC<RenameScenarioModalProps> = ({
  scenarioName,
  existingScenarioNames,
  instanceCount,
}) => {
  const renameScenario = useRenameScenarioMutation();

  function handleRename(newName: string) {
    renameScenario.mutate(
      { name: scenarioName, newName },
      {
        onSuccess: () => {
          showSuccessNotification(
            'Renamed',
            `Scenario "${scenarioName}" renamed to "${newName}"`
          );
          modals.closeAll();
        },
        onError: (error) =>
          showErrorNotification('Failed to rename scenario', error),
      }
    );
  }

  return (
    <RenameModal
      label="New scenario name"
      currentName={scenarioName}
      takenNames={existingScenarioNames}
      isPending={renameScenario.isPending}
      onRename={handleRename}
    >
      <Text size="sm" c="dimmed">
        The scenario tag will be rewritten in {instanceCount}{' '}
        {instanceCount === 1 ? 'instance' : 'instances'}.
      </Text>
    </RenameModal>
  );
};
