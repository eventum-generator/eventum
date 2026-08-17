import { ActionIcon, Badge, Button, Group, Text, Title } from '@mantine/core';
import {
  IconArrowLeft,
  IconDeviceFloppy,
  IconRefresh,
} from '@tabler/icons-react';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import { PipelineStrip } from './PipelineStrip';
import { useStudioConfig, useStudioShell } from './context';
import { UnsavedChangesPrompt } from '@/components/ui/UnsavedChangesPrompt';
import { ROUTE_PATHS } from '@/routing/paths';

export const CommandBar: FC = () => {
  const navigate = useNavigate();
  const { projectName, dirtyFileIds, saveFile, configError, reloadConfig } =
    useStudioShell();
  const { isConfigDirty, saveConfig, isSavingConfig } = useStudioConfig();

  const dirtyFiles = dirtyFileIds.length;
  const anyDirty = isConfigDirty || dirtyFiles > 0;

  function handleSaveAll() {
    if (isConfigDirty) {
      saveConfig();
    }
    for (const id of dirtyFileIds) {
      saveFile(id);
    }
  }

  // Leaving with unsaved changes is guarded globally by UnsavedChangesPrompt
  // (covers the sidebar and every other navigation, not just this button).
  function handleBack() {
    void navigate(ROUTE_PATHS.PROJECTS);
  }

  return (
    <>
      <UnsavedChangesPrompt when={anyDirty} />
      <div className="studio-commandbar">
        <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
          <ActionIcon
            variant="default"
            size="lg"
            onClick={handleBack}
            title="Back to projects"
          >
            <IconArrowLeft size={18} />
          </ActionIcon>
          <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
            <Text size="sm" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
              Projects /
            </Text>
            <Title
              order={4}
              fw={700}
              title={projectName}
              style={{
                letterSpacing: '-0.02em',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {projectName}
            </Title>
          </Group>
        </Group>

        {!configError && <PipelineStrip />}

        <Group gap="xs" wrap="nowrap">
          {configError ? (
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={reloadConfig}
            >
              Reload
            </Button>
          ) : (
            <>
              {anyDirty && (
                <Badge size="sm" variant="light" color="yellow">
                  {isConfigDirty && dirtyFiles > 0
                    ? `config + ${dirtyFiles} file${dirtyFiles > 1 ? 's' : ''}`
                    : isConfigDirty
                      ? 'config'
                      : `${dirtyFiles} file${dirtyFiles > 1 ? 's' : ''}`}
                </Badge>
              )}
              <Button
                leftSection={<IconDeviceFloppy size={16} />}
                disabled={!anyDirty}
                loading={isSavingConfig}
                onClick={handleSaveAll}
              >
                Save
              </Button>
            </>
          )}
        </Group>
      </div>
    </>
  );
};
