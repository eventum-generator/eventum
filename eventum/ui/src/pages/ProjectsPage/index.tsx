import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Center,
  Checkbox,
  Container,
  Group,
  Loader,
  Paper,
  Stack,
  TagsInput,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconAlertSquareRounded, IconSearch, IconX } from '@tabler/icons-react';
import { useState } from 'react';

import { CreateProjectModal } from './CreateProjectModal';
import { GeneratorDirsTable } from './GeneratorDirsTable';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function ProjectsPage() {
  const [projectNameFilter, setProjectNameFilter] = useState('');
  const [instanceFilter, setInstanceFilter] = useState<string[]>([]);
  const [anyInstanceFilter, setAnyInstanceFilter] = useState(false);

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
    const uniqueInstances = new Set(
      generatorDirs.flatMap((item) => item.generator_ids)
    );

    return (
      <Container size="100%">
        <Stack>
          <PageTitle title="Projects" />

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
                  disabled={anyInstanceFilter}
                />
                <Checkbox
                  label="Any used"
                  checked={anyInstanceFilter}
                  onChange={(event) =>
                    setAnyInstanceFilter(event.currentTarget.checked)
                  }
                />
              </Group>
              <Button
                onClick={() =>
                  modals.open({
                    title: 'New project',
                    children: (
                      <CreateProjectModal
                        existingProjectNames={generatorDirs.map(
                          (item) => item.name
                        )}
                      />
                    ),
                    size: 'lg',
                  })
                }
              >
                Create new
              </Button>
            </Group>
          </Paper>

          <GeneratorDirsTable
            data={generatorDirs}
            projectNameFilter={projectNameFilter}
            instancesFilter={instanceFilter}
            anyInstanceFilter={anyInstanceFilter}
          />
        </Stack>
      </Container>
    );
  }

  return <></>;
}
