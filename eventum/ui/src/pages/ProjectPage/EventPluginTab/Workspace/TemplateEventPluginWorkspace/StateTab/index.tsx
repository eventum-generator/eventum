import { Alert, Box, Center, Group, Select, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { FC, useState } from 'react';

import { useGetPluginConfig } from '../../../hooks/useGetPluginConfig';
import { TemplateState } from './TemplateState';
import {
  useClearTemplateEventPluginGlobalStateMutation,
  useClearTemplateEventPluginLocalStateMutation,
  useClearTemplateEventPluginSharedStateMutation,
  useTemplateEventPluginGlobalState,
  useTemplateEventPluginLocalState,
  useTemplateEventPluginSharedState,
  useUpdateTemplateEventPluginGlobalStateMutation,
  useUpdateTemplateEventPluginLocalStateMutation,
  useUpdateTemplateEventPluginSharedStateMutation,
} from '@/api/hooks/usePreview';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

export const StateTab: FC = () => {
  const { getPluginConfig } = useGetPluginConfig();
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  const pluginConfig = getPluginConfig();
  const templates = [];

  if ('template' in pluginConfig) {
    const templateNames = pluginConfig.template.templates.map(
      (item) => Object.keys(item)[0]!
    );
    templates.push(...templateNames);
  }

  return (
    <Stack gap="xs">
      <Group>
        <Select
          label={
            <LabelWithTooltip
              label="Template"
              tooltip="Template for which to display local state"
            />
          }
          placeholder="template name"
          data={templates}
          clearable
          searchable
          value={selectedTemplate}
          onChange={setSelectedTemplate}
        />
      </Group>

      <Group align="start" grow gap="xs">
        {selectedTemplate === null ? (
          <Center mih="100px">
            <Text size="sm" c="gray.6">
              Select template to display its local state
            </Text>
          </Center>
        ) : (
          <TemplateState
            stateName="Local state"
            templateAlias={selectedTemplate}
            useTemplateEventPluginState={useTemplateEventPluginLocalState}
            useUpdateTemplateEventPluginStateMutation={
              useUpdateTemplateEventPluginLocalStateMutation
            }
            useClearTemplateEventPluginStateMutation={
              useClearTemplateEventPluginLocalStateMutation
            }
          />
        )}

        <TemplateState
          stateName="Shared state"
          templateAlias=""
          useTemplateEventPluginState={useTemplateEventPluginSharedState}
          useUpdateTemplateEventPluginStateMutation={
            useUpdateTemplateEventPluginSharedStateMutation
          }
          useClearTemplateEventPluginStateMutation={
            useClearTemplateEventPluginSharedStateMutation
          }
        />
      </Group>

      <TemplateState
        stateName="Global state"
        templateAlias=""
        useTemplateEventPluginState={useTemplateEventPluginGlobalState}
        useUpdateTemplateEventPluginStateMutation={
          useUpdateTemplateEventPluginGlobalStateMutation
        }
        useClearTemplateEventPluginStateMutation={
          useClearTemplateEventPluginGlobalStateMutation
        }
      />
      <Alert
        variant="default"
        icon={<Box c="orange" component={IconAlertTriangle} />}
        title="Global state"
      >
        Updating global state will also affect to currently running generator
        instances.
      </Alert>
    </Stack>
  );
};
