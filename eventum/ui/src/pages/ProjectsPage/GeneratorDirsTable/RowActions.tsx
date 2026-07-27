import { Button, Group, List, Menu, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconCursorText, IconEdit, IconTrash } from '@tabler/icons-react';
import { FC, ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { RenameProjectModal } from '../RenameProjectModal';
import {
  useDeleteGeneratorConfigMutation,
  useGeneratorDirs,
} from '@/api/hooks/useGeneratorConfigs';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';
import { CONFIRM } from '@/theme/copy';

interface RowActionsProps {
  target: ReactNode;
  dirName: string;
  generatorIds: string[];
}

export const RowActions: FC<RowActionsProps> = ({
  target,
  dirName,
  generatorIds,
}) => {
  const deleteGeneratorConfig = useDeleteGeneratorConfigMutation();

  // Reads the list the table itself renders from, so no extra request.
  const { data: generatorDirs } = useGeneratorDirs(true);

  function handleRename() {
    modals.open({
      title: 'Rename project',
      children: (
        <RenameProjectModal
          projectName={dirName}
          existingProjectNames={(generatorDirs ?? []).map((dir) => dir.name)}
          instanceIds={generatorIds}
        />
      ),
      size: 'md',
    });
  }

  function handleDelete() {
    if (generatorIds.length > 0) {
      modals.open({
        title: 'Unable to delete',
        children: (
          <Stack gap="xs">
            <Text size="sm">
              There are instances that use this project. Please, delete them
              first to be able to delete project.
            </Text>
            <List size="sm" fw="bold">
              {generatorIds.map((item) => (
                <List.Item key={item}>{item}</List.Item>
              ))}
            </List>
            <Group justify="end">
              <Button onClick={() => modals.closeAll()} w="80px">
                Ok
              </Button>
            </Group>
          </Stack>
        ),
        size: 'md',
      });
      return;
    }

    modals.openConfirmModal({
      title: CONFIRM.deleteProject.title,
      children: <Text size="sm">{CONFIRM.deleteProject.body(dirName)}</Text>,
      size: 'md',
      labels: {
        cancel: CONFIRM.deleteProject.cancel,
        confirm: CONFIRM.deleteProject.confirm,
      },
      onConfirm: () =>
        deleteGeneratorConfig.mutate(
          { name: dirName },
          {
            onSuccess: () => {
              notifications.show({
                title: 'Success',
                message: 'Project was deleted',
                color: 'green',
              });
            },
            onError: (error) => {
              notifications.show({
                title: 'Error',
                message: (
                  <>
                    Failed to delete project.{' '}
                    <ShowErrorDetailsAnchor error={error} />
                  </>
                ),
                color: 'red',
              });
            },
          }
        ),
    });
  }
  return (
    <Menu shadow="md" width={170}>
      <Menu.Target>{target}</Menu.Target>

      <Menu.Dropdown>
        <Menu.Item
          component={Link}
          to={`${ROUTE_PATHS.PROJECTS}/${dirName}`}
          leftSection={<IconEdit size={14} />}
        >
          Edit
        </Menu.Item>

        <Menu.Item
          leftSection={<IconCursorText size={14} />}
          onClick={handleRename}
        >
          Rename
        </Menu.Item>

        <Menu.Divider />

        <Menu.Item
          color="var(--mantine-color-red-text)"
          leftSection={<IconTrash size={14} />}
          onClick={handleDelete}
        >
          Delete
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
};
