import { CodeHighlight } from '@mantine/code-highlight';
import { Box, Center, Grid, Paper, Stack, Tabs, Text } from '@mantine/core';
import { FC, useCallback, useEffect, useRef, useState } from 'react';
import YAML from 'yaml';

import { OutputPluginsList } from '../PluginsList';
import { EditorTab } from '../common/EditorTab';
import { FileTree } from '../common/FileTree';
import { FormatterTab } from './FormatterTab';
import { OutputPluginParams } from './OutputPluginParams';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { OutputPluginsNamedConfig } from '@/api/routes/generator-configs/schemas';
import { OutputPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/output';
import { OutputPluginName } from '@/api/routes/generator-configs/schemas/plugins/output/base-config';

interface OutputPluginsTabProps {
  initialOutputPluginsConfig: OutputPluginsNamedConfig;
  onOutputPluginsConfigChange: (config: OutputPluginsNamedConfig) => void;
}

export const OutputPluginsTab: FC<OutputPluginsTabProps> = ({
  initialOutputPluginsConfig,
  onOutputPluginsConfigChange,
}) => {
  const [selectedPluginIndex, setSelectedPluginIndex] = useState(0);
  const [pluginsConfig, setPluginsConfig] = useState<OutputPluginsNamedConfig>(
    initialOutputPluginsConfig
  );
  const [pluginNames, setPluginNames] = useState<string[]>(
    pluginsConfig.map((plugin) => Object.keys(plugin)[0]!)
  );

  useEffect(() => {
    onOutputPluginsConfigChange(pluginsConfig);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pluginsConfig]);

  const handleAddNewPlugin = useCallback(
    (pluginType: 'output', pluginName: OutputPluginName) => {
      const defaultConfig = PLUGIN_DEFAULT_CONFIGS[pluginType][pluginName];

      setPluginsConfig(
        (pluginsConfig) =>
          [
            ...pluginsConfig,
            { [pluginName]: defaultConfig },
          ] as OutputPluginsNamedConfig
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

  const handleConfigChange = useCallback(
    (config: OutputPluginNamedConfig) => {
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
              <OutputPluginsList
                type="output"
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
              <Tabs defaultValue="formatter">
                <Tabs.List>
                  <Tabs.Tab value="formatter">Formatter</Tabs.Tab>
                  <Tabs.Tab value="editor">Editor</Tabs.Tab>
                </Tabs.List>

                <Box mt="md">
                  <Tabs.Panel value="formatter">
                    <FormatterTab />
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
                <OutputPluginParams
                  outputPluginConfig={pluginsConfig[selectedPluginIndex]!}
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
