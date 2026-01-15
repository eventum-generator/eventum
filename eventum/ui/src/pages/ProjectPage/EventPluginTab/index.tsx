import { CodeHighlight } from '@mantine/code-highlight';
import { Center, Grid, Paper, Stack, Text } from '@mantine/core';
import { FC, useCallback, useEffect, useState } from 'react';
import YAML from 'yaml';

import { EventPluginsList } from '../PluginsList';
import { FileTree } from '../common/FileTree';
import { EventPluginParams } from './EventPluginParams';
import { Workspace } from './Workspace';
import { GetPluginConfigProvider } from './context/GetPluginConfigContext';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { EventPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/event';
import { EventPluginName } from '@/api/routes/generator-configs/schemas/plugins/event/base-config';

interface EventPluginTabProps {
  initialEventPluginConfig: EventPluginNamedConfig;
  onEventPluginConfigChange: (config: EventPluginNamedConfig) => void;
}

export const EventPluginTab: FC<EventPluginTabProps> = ({
  initialEventPluginConfig,
  onEventPluginConfigChange,
}) => {
  const [selectedPluginIndex, setSelectedPluginIndex] = useState(0);
  const [pluginsConfig, setPluginsConfig] = useState<EventPluginNamedConfig[]>([
    initialEventPluginConfig,
  ]);
  const [pluginNames, setPluginNames] = useState<string[]>(
    pluginsConfig.map((plugin) => Object.keys(plugin)[0]!)
  );

  useEffect(() => {
    onEventPluginConfigChange(pluginsConfig[0]!);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pluginsConfig]);

  const handleAddNewPlugin = useCallback(
    (pluginType: 'event', pluginName: EventPluginName) => {
      const defaultConfig = PLUGIN_DEFAULT_CONFIGS[pluginType][pluginName];

      setPluginsConfig([
        {
          [pluginName]: defaultConfig,
        },
      ] as EventPluginNamedConfig[]);

      setPluginNames([pluginName]);
    },
    []
  );

  const handleDeletePlugin = useCallback(() => {
    setPluginsConfig([]);
    setPluginNames([]);
  }, []);

  const handleConfigChange = useCallback((config: EventPluginNamedConfig) => {
    setPluginsConfig([config]);
  }, []);

  return (
    <Grid>
      <Grid.Col span={2}>
        <Stack>
          <Paper withBorder p="sm">
            <Stack gap="xs">
              <Text size="sm" fw="bold">
                Plugin list
              </Text>
              <EventPluginsList
                type="event"
                plugins={pluginNames}
                onChangeSelectedPlugin={setSelectedPluginIndex}
                selectedPlugin={selectedPluginIndex}
                onAddNewPlugin={handleAddNewPlugin}
                onDeletePlugin={handleDeletePlugin}
                maxPlugins={1}
              />
            </Stack>
          </Paper>
          <Paper withBorder p="sm">
            <Stack gap="xs">
              <Text size="sm" fw="bold">
                File tree
              </Text>
              <FileTree />
            </Stack>
          </Paper>
        </Stack>
      </Grid.Col>
      <Grid.Col span={7}>
        <Paper withBorder p="sm">
          <Stack gap="xs">
            <Text size="sm" fw="bold">
              Workspace
            </Text>
            {pluginsConfig.length === 0 ? (
              <Center>
                <Text size="sm" c="gray.6">
                  No plugins added
                </Text>
              </Center>
            ) : (
              <GetPluginConfigProvider
                getPluginConfig={() => pluginsConfig[0]!}
              >
                <Workspace
                  pluginName={
                    Object.keys(pluginsConfig[0]!)[0] as EventPluginName
                  }
                />
              </GetPluginConfigProvider>
            )}
          </Stack>
        </Paper>
      </Grid.Col>
      <Grid.Col span={3}>
        <Stack>
          <Paper withBorder p="sm">
            <Stack gap="xs">
              <Text size="sm" fw="bold">
                Plugin parameters
              </Text>
              {pluginsConfig.length === 0 ? (
                <Center>
                  <Text size="sm" c="gray.6">
                    No plugins added
                  </Text>
                </Center>
              ) : (
                <EventPluginParams
                  eventPluginConfig={pluginsConfig[0]!}
                  onChange={handleConfigChange}
                />
              )}
            </Stack>
          </Paper>
          {pluginsConfig.length > 0 && (
            <Paper withBorder p="sm">
              <Stack gap="xs">
                <Text size="sm" fw="bold">
                  Configuration preview
                </Text>
                <CodeHighlight
                  code={YAML.stringify(pluginsConfig[0]!)}
                  language="yml"
                />
              </Stack>
            </Paper>
          )}
        </Stack>
      </Grid.Col>
    </Grid>
  );
};
