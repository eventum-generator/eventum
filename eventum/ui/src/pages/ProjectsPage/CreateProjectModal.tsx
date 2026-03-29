import { Stack } from '@mantine/core';
import { modals } from '@mantine/modals';
import { FC } from 'react';

import {
  CreateProjectSubmitModal,
  CreateProjectSubmitModalProps,
} from './ProjectNameModal';
import { EVENT_PLUGINS_INFO } from '@/api/routes/generator-configs/modules/plugins/registry';
import { EventPluginName } from '@/api/routes/generator-configs/schemas/plugins/event/base-config';
import { AreaButton } from '@/components/ui/AreaButton';

interface CreateProjectModalProps {
  existingProjectNames: string[];
  onCreated?: (projectName: string) => void;
}

export const CreateProjectModal: FC<CreateProjectModalProps> = ({
  existingProjectNames,
  onCreated,
}) => {
  function handleCreateProject(
    projectType: CreateProjectSubmitModalProps['projectType']
  ) {
    modals.open({
      title: 'Creating project',
      children: (
        <CreateProjectSubmitModal
          existingProjectNames={existingProjectNames}
          projectType={projectType}
          onCreated={onCreated}
        />
      ),
    });
  }

  return (
    <Stack>
      {Object.entries(EVENT_PLUGINS_INFO).map(
        ([name, { label, description, icon: PluginIcon }]) => (
          <AreaButton
            key={name}
            icon={PluginIcon}
            name={label}
            description={description}
            onClick={() => handleCreateProject(name as EventPluginName)}
          />
        )
      )}
    </Stack>
  );
};
