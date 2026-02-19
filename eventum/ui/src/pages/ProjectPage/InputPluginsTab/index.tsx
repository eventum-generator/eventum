import { CodeHighlight } from '@mantine/code-highlight';
import { Box, Center, Grid, Paper, Stack, Tabs, Text } from '@mantine/core';
import { FC, useCallback, useEffect, useRef, useState } from 'react';
import YAML from 'yaml';

import { InputPluginsList } from '../PluginsList';
import { EditorTab } from '../common/EditorTab';
import { FileTree } from '../common/FileTree';
import { InputPluginParams } from './InputPluginParams';
import TimestampsHistogram from './TimestampsHistogram';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { InputPluginsNamedConfig } from '@/api/routes/generator-configs/schemas';
import { InputPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/input';
import { InputPluginName } from '@/api/routes/generator-configs/schemas/plugins/input/base-config';

interface InputPluginsTabProps {
  initialInputPluginsConfig: InputPluginsNamedConfig;
  onInputPluginsConfigChange: (config: InputPluginsNamedConfig) => void;
}

export const InputPluginsTab: FC<InputPluginsTabProps> = ({
  initialInputPluginsConfig,
  onInputPluginsConfigChange,
}) => {
  const [selectedPluginIndex, setSelectedPluginIndex] = useState(0);
  const [pluginsConfig, setPluginsConfig] = useState<InputPluginsNamedConfig>(
    initialInputPluginsConfig
  );
  const [pluginNames, setPluginNames] = useState<string[]>(
    pluginsConfig.map((plugin) => Object.keys(plugin)[0]!)
  );

  useEffect(() => {
    onInputPluginsConfigChange(pluginsConfig);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pluginsConfig]);

  const handleAddNewPlugin = useCallback(
    (pluginType: 'input', pluginName: InputPluginName) => {
      const defaultConfig = PLUGIN_DEFAULT_CONFIGS[pluginType][pluginName];

      setPluginsConfig(
        (pluginsConfig) =>
          [
            ...pluginsConfig,
            { [pluginName]: defaultConfig },
          ] as InputPluginsNamedConfig
      );
      setPluginNames((value) => [...value, pluginName]);
    },
    []
  );

  const handleDeletePlugin = useCallback((index: number) => {
    setPluginsConfig((pluginsConfig) => {
      const newConfig = [
        ...pluginsConfig.slice(0, index),
        ...pluginsConfig.slice(index + 1),
      ];

      setSelectedPluginIndex((selectedPluginIndex) =>
        selectedPluginIndex >= newConfig.length
          ? Math.max(newConfig.length - 1, 0)
          : selectedPluginIndex
      );

      return newConfig;
    });

    setPluginNames((value) => [
      ...value.slice(0, index),
      ...value.slice(index + 1),
    ]);
  }, []);

  const pluginsConfigRef = useRef(pluginsConfig);
  pluginsConfigRef.current = pluginsConfig;

  const getInputPluginsConfig = useCallback(() => {
    return pluginsConfigRef.current;
  }, []);

  const selectedPluginIndexRef = useRef(selectedPluginIndex);
  selectedPluginIndexRef.current = selectedPluginIndex;

  const getSelectedPluginIndex = useCallback(() => {
    return selectedPluginIndexRef.current;
  }, []);

  const handleConfigChange = useCallback(
    (config: InputPluginNamedConfig) => {
      const newConfig = [...pluginsConfig];
      newConfig[selectedPluginIndex] = config;

      setPluginsConfig(newConfig);
    },
    [pluginsConfig, selectedPluginIndex]
  );
  return (
    <Grid>
      <Grid.Col span={2}>
        <Stack>
          <Paper withBorder p="sm">
            <Stack gap="xs">
              <Text size="sm" fw="bold">
                Plugin list
              </Text>
              <InputPluginsList
                type="input"
                plugins={pluginNames}
                onChangeSelectedPlugin={setSelectedPluginIndex}
                selectedPlugin={selectedPluginIndex}
                onAddNewPlugin={handleAddNewPlugin}
                onDeletePlugin={handleDeletePlugin}
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
              <Tabs defaultValue="preview">
                <Tabs.List>
                  <Tabs.Tab value="preview">Preview</Tabs.Tab>
                  <Tabs.Tab value="editor">Editor</Tabs.Tab>
                </Tabs.List>

                <Box mt="md">
                  <Tabs.Panel value="preview">
                    <TimestampsHistogram
                      getSelectedPluginIndex={getSelectedPluginIndex}
                      getInputPluginsConfig={getInputPluginsConfig}
                    />
                  </Tabs.Panel>
                  <Tabs.Panel value="editor">
                    <EditorTab />
                  </Tabs.Panel>
                </Box>
              </Tabs>
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
                <InputPluginParams
                  inputPluginConfig={pluginsConfig[selectedPluginIndex]!}
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
                  code={YAML.stringify(pluginsConfig[selectedPluginIndex]!)}
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
