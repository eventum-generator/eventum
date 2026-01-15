import {
  ActionIcon,
  Button,
  Center,
  NavLink,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { Icon, IconPlus, IconTrash } from '@tabler/icons-react';
import { memo } from 'react';

import {
  PLUGINS_INFO,
  PluginNamesMap,
  PluginType,
} from '@/api/routes/generator-configs/modules/plugins/registry';
import { AreaButton } from '@/components/ui/AreaButton';

interface PluginsListProps<T extends PluginType> {
  type: T;
  plugins: string[];
  onChangeSelectedPlugin: (index: number) => void;
  selectedPlugin: number;
  onAddNewPlugin: (pluginType: T, pluginName: PluginNamesMap[T]) => void;
  onDeletePlugin: (index: number) => void;
  maxPlugins?: number;
}

const PluginsList = <T extends PluginType>({
  type,
  plugins,
  onChangeSelectedPlugin,
  selectedPlugin,
  onAddNewPlugin,
  onDeletePlugin,
  maxPlugins,
}: PluginsListProps<T>) => {
  function handleDeletePlugin(index: number) {
    modals.openConfirmModal({
      title: 'Deleting plugin',
      children: (
        <Text size="sm">
          Plugin{' '}
          <b>
            {plugins[index]} #{index + 1}
          </b>{' '}
          will be deleted. Do you want to continue?
        </Text>
      ),
      labels: { cancel: 'Cancel', confirm: 'Confirm' },
      onConfirm: () => {
        onDeletePlugin(index);
        modals.closeAll();
      },
    });
  }

  function handleAddPlugin() {
    modals.open({
      title: 'Adding plugin',
      children: (
        <Stack>
          {Object.entries(PLUGINS_INFO[type]).map(
            ([name, { label, icon: PluginIcon, description }]) => (
              <AreaButton
                key={name}
                icon={PluginIcon as Icon}
                name={label as string}
                description={description as string}
                onClick={() => {
                  onAddNewPlugin(type, name as PluginNamesMap[typeof type]);
                  modals.closeAll();
                }}
                h="75px"
                gap="4px"
              />
            )
          )}
        </Stack>
      ),
      size: 'lg',
    });
  }

  return (
    <Stack gap="xs">
      <Stack gap="xs">
        {plugins.length === 0 && (
          <Center>
            <Text size="sm" c="gray.6">
              No plugins added
            </Text>
          </Center>
        )}
        {plugins.map((item, idx) => (
          <NavLink
            key={idx}
            label={`${item} #${idx + 1}`}
            active={idx === selectedPlugin}
            style={{ borderRadius: '8px' }}
            p="4px 4px 4px 12px"
            onClick={() => onChangeSelectedPlugin(idx)}
            rightSection={
              <ActionIcon
                variant="transparent"
                c="red"
                title="Remove"
                size="lg"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeletePlugin(idx);
                }}
              >
                <IconTrash size={20} />
              </ActionIcon>
            }
          />
        ))}
      </Stack>
      <Button
        variant="default"
        title="Add new plugin"
        onClick={handleAddPlugin}
        disabled={maxPlugins !== undefined && plugins.length >= maxPlugins}
      >
        <IconPlus size={20} />
      </Button>
    </Stack>
  );
};

export const InputPluginsList = memo(PluginsList<'input'>);
export const EventPluginsList = memo(PluginsList<'event'>);
export const OutputPluginsList = memo(PluginsList<'output'>);
