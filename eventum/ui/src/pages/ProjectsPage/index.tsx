import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Paper,
  SegmentedControl,
  Stack,
  TagsInput,
  Text,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconAlertSquareRounded, IconSearch, IconX } from '@tabler/icons-react';
import { useState } from 'react';

import { CreateProjectModal } from './CreateProjectModal';
import { GeneratorDirsTable, UsageMode } from './GeneratorDirsTable';
import { ProjectsEmptyState } from './ProjectsEmptyState';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function ProjectsPage() {
  const [projectNameFilter, setProjectNameFilter] = useState('');
  const [instanceFilter, setInstanceFilter] = useState<string[]>([]);
  const [usageMode, setUsageMode] = useState<UsageMode>('all');

  const {
    data: generatorDirs,
    isLoading: isGeneratorDirsLoading,
    isError: isGeneratorDirsError,
    error: generatorDirsError,
    isSuccess: isGeneratorDirsSuccess,
  } = useGeneratorDirs(true);

  if (isGeneratorDirsLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isGeneratorDirsError) {
    return (
      <Container size="md" mt="lg">
        <PageTitle title="Projects" />
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to load projects list"
        >
          {generatorDirsError.message}
          <ShowErrorDetailsAnchor error={generatorDirsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isGeneratorDirsSuccess) {
    const openCreateModal = () =>
      modals.open({
        title: 'New project',
        children: (
          <CreateProjectModal
            existingProjectNames={generatorDirs.map((item) => item.name)}
          />
        ),
        size: 'lg',
      });

    const total = generatorDirs.length;

    if (total === 0) {
      return (
        <Container size="100%">
          <Stack>
            <PageTitle title="Projects" />
            <ProjectsEmptyState onCreate={openCreateModal} />
          </Stack>
        </Container>
      );
    }

    const inUse = generatorDirs.filter(
      (item) => item.generator_ids.length > 0
    ).length;
    const uniqueInstances = new Set(
      generatorDirs.flatMap((item) => item.generator_ids)
    );

    return (
      <Container size="100%">
        <Stack>
          <Group align="baseline" gap="sm">
            <PageTitle title="Projects" />
            <Text size="sm" c="dimmed">
              {total} {total === 1 ? 'project' : 'projects'} · {inUse} in use
            </Text>
          </Group>

          <Paper withBorder p="sm">
            <Group justify="space-between">
              <Group>
                <TextInput
                  leftSection={<IconSearch size={16} />}
                  rightSection={
                    <ActionIcon
                      variant="transparent"
                      onClick={() => setProjectNameFilter('')}
                      data-input-section
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  }
                  placeholder="search by name..."
                  value={projectNameFilter}
                  onChange={(event) => setProjectNameFilter(event.target.value)}
                />
                <TagsInput
                  leftSection={<IconSearch size={16} />}
                  placeholder="search by instance"
                  clearable
                  data={[...uniqueInstances].sort((a, b) => a.localeCompare(b))}
                  value={instanceFilter}
                  onChange={(values) => setInstanceFilter(values)}
                  disabled={usageMode === 'unused'}
                />
                <SegmentedControl
                  value={usageMode}
                  onChange={(value) => {
                    const mode = value as UsageMode;
                    setUsageMode(mode);
                    if (mode === 'unused') setInstanceFilter([]);
                  }}
                  data={[
                    { label: 'All', value: 'all' },
                    { label: 'In use', value: 'used' },
                    { label: 'Unused', value: 'unused' },
                  ]}
                />
              </Group>
              <Button onClick={openCreateModal}>Create new</Button>
            </Group>
          </Paper>

          <GeneratorDirsTable
            data={generatorDirs}
            projectNameFilter={projectNameFilter}
            instancesFilter={instanceFilter}
            usageMode={usageMode}
          />
        </Stack>
      </Container>
    );
  }

  return <></>;
}
