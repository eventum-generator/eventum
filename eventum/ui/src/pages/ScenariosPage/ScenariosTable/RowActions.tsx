import { Menu, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconEdit, IconTrash } from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { useDeleteScenario } from '../useDeleteScenario';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

interface RowActionsProps {
  target: ReactNode;
  scenarioName: string;
  startupEntries: StartupGeneratorParametersList;
}

export const RowActions: FC<RowActionsProps> = ({
  target,
  scenarioName,
  startupEntries,
}) => {
  const navigate = useNavigate();
  const deleteScenario = useDeleteScenario();

  function handleEdit() {
    void navigate(`/scenarios/${encodeURIComponent(scenarioName)}`);
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
          { scenarioName, startupEntries },
          {
            onSuccess: () => {
              notifications.show({
                title: 'Success',
                message: `Scenario "${scenarioName}" deleted`,
                color: 'green',
              });
            },
            onError: (deleteError) => {
              notifications.show({
                title: 'Error',
                message: (
                  <>
                    Failed to delete scenario
                    <ShowErrorDetailsAnchor error={deleteError} prependDot />
                  </>
                ),
                color: 'red',
              });
            },
          }
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
