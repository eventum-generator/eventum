import { Select } from '@mantine/core';
import { FC, useState } from 'react';

import {
  ToolBody,
  ToolEmpty,
  ToolPane,
  ToolShell,
} from '../../../../studio/panels/console/primitives';
import { useGetPluginConfig } from '../../../hooks/useGetPluginConfig';
import { TemplateState } from './TemplateState';
import {
  useClearTemplateEventPluginGlobalStateMutation,
  useClearTemplateEventPluginLocalStateMutation,
  useClearTemplateEventPluginSharedStateMutation,
  useDeleteTemplateEventPluginGlobalStateKeyMutation,
  useDeleteTemplateEventPluginLocalStateKeyMutation,
  useDeleteTemplateEventPluginSharedStateKeyMutation,
  useTemplateEventPluginGlobalState,
  useTemplateEventPluginLocalState,
  useTemplateEventPluginSharedState,
  useUpdateTemplateEventPluginGlobalStateMutation,
  useUpdateTemplateEventPluginLocalStateMutation,
  useUpdateTemplateEventPluginSharedStateMutation,
} from '@/api/hooks/usePreview';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

export const StateTab: FC = () => {
  const { getPluginConfig } = useGetPluginConfig();
  const { projectName } = useProjectName();
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  const pluginConfig = getPluginConfig();
  const templates = [];

  if ('template' in pluginConfig) {
    const templateNames = pluginConfig.template.templates.map(
      (item) => Object.keys(item)[0]!
    );
    templates.push(...templateNames);
  }

  // Local state hooks
  const localState = useTemplateEventPluginLocalState(
    projectName,
    selectedTemplate ?? ''
  );
  const updateLocalState = useUpdateTemplateEventPluginLocalStateMutation();
  const deleteLocalStateKey =
    useDeleteTemplateEventPluginLocalStateKeyMutation();
  const clearLocalState = useClearTemplateEventPluginLocalStateMutation();

  // Shared state hooks
  const sharedState = useTemplateEventPluginSharedState(projectName);
  const updateSharedState = useUpdateTemplateEventPluginSharedStateMutation();
  const deleteSharedStateKey =
    useDeleteTemplateEventPluginSharedStateKeyMutation();
  const clearSharedState = useClearTemplateEventPluginSharedStateMutation();

  // Global state hooks
  const globalState = useTemplateEventPluginGlobalState(projectName);
  const updateGlobalState = useUpdateTemplateEventPluginGlobalStateMutation();
  const deleteGlobalStateKey =
    useDeleteTemplateEventPluginGlobalStateKeyMutation();
  const clearGlobalState = useClearTemplateEventPluginGlobalStateMutation();

  return (
    <ToolShell
      toolbar={
        <Select
          w={240}
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
      }
    >
      <ToolBody>
        <ToolPane>
          {selectedTemplate === null ? (
            <ToolEmpty>Select a template to inspect its local state.</ToolEmpty>
          ) : (
            <TemplateState
              stateName="Local state"
              data={localState.data}
              isLoading={localState.isLoading}
              isError={localState.isError}
              error={localState.error}
              isSuccess={localState.isSuccess}
              refetch={() => void localState.refetch()}
              onUpdateKey={(key, value) => {
                updateLocalState.mutate(
                  {
                    name: projectName,
                    templateAlias: selectedTemplate,
                    state: { [key]: value },
                  },
                  {
                    onSuccess: () =>
                      showSuccessNotification(
                        'Updated',
                        `Key "${key}" updated`
                      ),
                    onError: (e) =>
                      showErrorNotification('Failed to update key', e),
                  }
                );
              }}
              onDeleteKey={(key) => {
                deleteLocalStateKey.mutate(
                  {
                    name: projectName,
                    templateAlias: selectedTemplate,
                    key,
                  },
                  {
                    onSuccess: () =>
                      showSuccessNotification(
                        'Deleted',
                        `Key "${key}" removed`
                      ),
                    onError: (e) =>
                      showErrorNotification('Failed to delete key', e),
                  }
                );
              }}
              onClear={() => {
                clearLocalState.mutate(
                  { name: projectName, templateAlias: selectedTemplate },
                  {
                    onSuccess: () =>
                      showSuccessNotification('Cleared', 'Local state cleared'),
                    onError: (e) =>
                      showErrorNotification('Failed to clear state', e),
                  }
                );
              }}
              isClearPending={clearLocalState.isPending}
            />
          )}
        </ToolPane>

        <ToolPane>
          <TemplateState
            stateName="Shared state"
            data={sharedState.data}
            isLoading={sharedState.isLoading}
            isError={sharedState.isError}
            error={sharedState.error}
            isSuccess={sharedState.isSuccess}
            refetch={() => void sharedState.refetch()}
            onUpdateKey={(key, value) => {
              updateSharedState.mutate(
                { name: projectName, state: { [key]: value } },
                {
                  onSuccess: () =>
                    showSuccessNotification('Updated', `Key "${key}" updated`),
                  onError: (e) =>
                    showErrorNotification('Failed to update key', e),
                }
              );
            }}
            onDeleteKey={(key) => {
              deleteSharedStateKey.mutate(
                { name: projectName, key },
                {
                  onSuccess: () =>
                    showSuccessNotification('Deleted', `Key "${key}" removed`),
                  onError: (e) =>
                    showErrorNotification('Failed to delete key', e),
                }
              );
            }}
            onClear={() => {
              clearSharedState.mutate(
                { name: projectName },
                {
                  onSuccess: () =>
                    showSuccessNotification('Cleared', 'Shared state cleared'),
                  onError: (e) =>
                    showErrorNotification('Failed to clear state', e),
                }
              );
            }}
            isClearPending={clearSharedState.isPending}
          />
        </ToolPane>

        <ToolPane>
          <TemplateState
            stateName="Global state"
            data={globalState.data}
            isLoading={globalState.isLoading}
            isError={globalState.isError}
            error={globalState.error}
            isSuccess={globalState.isSuccess}
            refetch={() => void globalState.refetch()}
            onUpdateKey={(key, value) => {
              updateGlobalState.mutate(
                { name: projectName, state: { [key]: value } },
                {
                  onSuccess: () =>
                    showSuccessNotification('Updated', `Key "${key}" updated`),
                  onError: (e) =>
                    showErrorNotification('Failed to update key', e),
                }
              );
            }}
            onDeleteKey={(key) => {
              deleteGlobalStateKey.mutate(
                { name: projectName, key },
                {
                  onSuccess: () =>
                    showSuccessNotification('Deleted', `Key "${key}" removed`),
                  onError: (e) =>
                    showErrorNotification('Failed to delete key', e),
                }
              );
            }}
            onClear={() => {
              clearGlobalState.mutate(
                { name: projectName },
                {
                  onSuccess: () =>
                    showSuccessNotification('Cleared', 'Global state cleared'),
                  onError: (e) =>
                    showErrorNotification('Failed to clear state', e),
                }
              );
            }}
            isClearPending={clearGlobalState.isPending}
            warningTitle="Shared across generators"
            warningMessage="Updating global state affects all currently running generator instances."
          />
        </ToolPane>
      </ToolBody>
    </ToolShell>
  );
};
