import { List, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import {
  PROJECT_NAME_PATTERN_ERROR,
  VALID_PROJECT_NAME_PATTERN,
} from './project-name';
import { useRenameGeneratorConfigMutation } from '@/api/hooks/useGeneratorConfigs';
import { RenameModal } from '@/components/modals/RenameModal';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RenameProjectModalProps {
  projectName: string;
  existingProjectNames: string[];
  instanceIds: string[];
}

export const RenameProjectModal: FC<RenameProjectModalProps> = ({
  projectName,
  existingProjectNames,
  instanceIds,
}) => {
  const renameProject = useRenameGeneratorConfigMutation();

  function handleRename(newName: string) {
    renameProject.mutate(
      { name: projectName, newName },
      {
        onSuccess: () => {
          showSuccessNotification(
            'Renamed',
            `Project "${projectName}" renamed to "${newName}"`
          );
          modals.closeAll();
        },
        onError: (error) =>
          showErrorNotification('Failed to rename project', error),
      }
    );
  }

  return (
    <RenameModal
      label="New project name"
      currentName={projectName}
      takenNames={existingProjectNames}
      pattern={VALID_PROJECT_NAME_PATTERN}
      patternError={PROJECT_NAME_PATTERN_ERROR}
      isPending={renameProject.isPending}
      onRename={handleRename}
    >
      {instanceIds.length > 0 ? (
        <Text size="sm">
          These instances use the project and will be repointed at the new name.
          All of them must be stopped.
          <List size="sm" mt="xs" fw={600}>
            {instanceIds.map((id) => (
              <List.Item key={id}>{id}</List.Item>
            ))}
          </List>
        </Text>
      ) : (
        <Text size="sm" c="dimmed">
          No instance uses this project.
        </Text>
      )}
    </RenameModal>
  );
};
