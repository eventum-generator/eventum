import { Button, Group, Image, Title } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconPlus } from '@tabler/icons-react';
import { FC } from 'react';
import { generatePath, useNavigate } from 'react-router-dom';

import { CreateProjectModal } from '@/pages/ProjectsPage/CreateProjectModal';
import { ROUTE_PATHS } from '@/routing/paths';

interface TopBandProps {
  existingProjectNames: string[];
}

export const TopBand: FC<TopBandProps> = ({ existingProjectNames }) => {
  const navigate = useNavigate();

  const openNewProject = () =>
    modals.open({
      title: 'New project',
      size: 'lg',
      children: (
        <CreateProjectModal
          existingProjectNames={existingProjectNames}
          onCreated={(name) =>
            void navigate(
              generatePath(ROUTE_PATHS.PROJECT, { projectName: name })
            )
          }
        />
      ),
    });

  return (
    <Group justify="space-between" align="center" wrap="wrap" gap="md">
      <Group gap="md" wrap="nowrap">
        <Image src="/logo.svg" alt="Eventum" w={40} h={40} />
        <Title order={2} fz="1.5rem" fw={650}>
          Eventum Studio
        </Title>
      </Group>

      <Button leftSection={<IconPlus size={18} />} onClick={openNewProject}>
        New project
      </Button>
    </Group>
  );
};
