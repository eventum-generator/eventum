import {
  ActionIcon,
  Alert,
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
import { IconSearch, IconX } from '@tabler/icons-react';
import { useMemo } from 'react';

import { CreateProjectModal } from './CreateProjectModal';
import { GeneratorDirsTable, UsageMode } from './GeneratorDirsTable';
import { ProjectsEmptyState } from './ProjectsEmptyState';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useTableQueryParams } from '@/utils/useTableQueryParams';

export default function ProjectsPage() {
  const { searchParams, setParams } = useTableQueryParams();
  const projectNameFilter = searchParams.get('q') ?? '';
  const rawUsage = searchParams.get('usage');
  const usageMode: UsageMode =
    rawUsage === 'used' || rawUsage === 'unused' ? rawUsage : 'all';
  const instanceFilter = useMemo(() => {
    const raw = searchParams.get('instances');
    return raw ? raw.split(',').filter(Boolean) : [];
  }, [searchParams]);

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
          icon={<AlertIcon variant="error" />}
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
                      onClick={() => setParams({ q: null })}
                      data-input-section
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  }
                  placeholder="search by name..."
                  value={projectNameFilter}
                  onChange={(event) =>
                    setParams({ q: event.target.value || null })
                  }
                />
                <TagsInput
                  leftSection={<IconSearch size={16} />}
                  placeholder="search by instance"
                  clearable
                  data={[...uniqueInstances].sort((a, b) => a.localeCompare(b))}
                  value={instanceFilter}
                  onChange={(values) => setParams({ instances: values })}
                  disabled={usageMode === 'unused'}
                />
                <SegmentedControl
                  value={usageMode}
                  onChange={(value) => {
                    const mode = value as UsageMode;
                    setParams({
                      usage: mode === 'all' ? null : mode,
                      ...(mode === 'unused' ? { instances: null } : {}),
                    });
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
