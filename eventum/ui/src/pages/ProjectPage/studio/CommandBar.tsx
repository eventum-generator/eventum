import { ActionIcon, Badge, Button, Group, Text, Title } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconArrowLeft, IconDeviceFloppy } from '@tabler/icons-react';
import { FC } from 'react';
import { useNavigate } from 'react-router-dom';

import { PipelineStrip } from './PipelineStrip';
import { useStudioConfig, useStudioShell } from './context';
import { ROUTE_PATHS } from '@/routing/paths';

export const CommandBar: FC = () => {
  const navigate = useNavigate();
  const { projectName, dirtyFileIds, saveFile } = useStudioShell();
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

  function handleBack() {
    if (anyDirty) {
      modals.openConfirmModal({
        title: 'Unsaved changes',
        children: (
          <Text size="sm">
            Project <b>{projectName}</b> has unsaved changes that will be lost.
            Continue?
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Discard and leave' },
        confirmProps: { color: 'red' },
        onConfirm: () => void navigate(ROUTE_PATHS.PROJECTS),
      });
    } else {
      void navigate(ROUTE_PATHS.PROJECTS);
    }
  }

  return (
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
          <Text size="sm" c="dimmed">
            Projects /
          </Text>
          <Title order={4} fw={700} style={{ letterSpacing: '-0.02em' }}>
            {projectName}
          </Title>
        </Group>
      </Group>

      <PipelineStrip />

      <Group gap="xs" wrap="nowrap">
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
      </Group>
    </div>
  );
};
