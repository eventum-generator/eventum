import { Menu, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconEdit, IconTrash } from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { useDeleteScenarioMutation } from '@/api/hooks/useScenarios';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

interface RowActionsProps {
  target: ReactNode;
  scenarioName: string;
}

export const RowActions: FC<RowActionsProps> = ({
  target,
  scenarioName,
}) => {
  const navigate = useNavigate();
  const deleteScenario = useDeleteScenarioMutation();

  function handleEdit() {
    void navigate(
      `${ROUTE_PATHS.SCENARIOS}/${encodeURIComponent(scenarioName)}`,
    );
  }

  function handleDelete() {
    modals.openConfirmModal({
      title: 'Delete scenario',
      children: (
        <Text size="sm">
          Delete scenario <b>{scenarioName}</b>? Generators will not be
          deleted.
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Delete' },
      onConfirm: () => {
        deleteScenario.mutate(
          scenarioName,
          {
            onSuccess: () =>
              showSuccessNotification(
                'Deleted',
                `Scenario "${scenarioName}" deleted`,
              ),
            onError: (deleteError) =>
              showErrorNotification('Failed to delete scenario', deleteError),
          },
        );
      },
    });
  }

  return (
    <Menu shadow="md" width={170}>
      <Menu.Target>{target}</Menu.Target>

      <Menu.Dropdown>
        <Menu.Item
          leftSection={<IconEdit size={14} />}
          onClick={handleEdit}
        >
          Edit
        </Menu.Item>

        <Menu.Divider />

        <Menu.Item
          color="red"
          leftSection={<IconTrash size={14} />}
          onClick={handleDelete}
        >
          Delete
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};
