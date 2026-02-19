import {
  Alert,
  Anchor,
  Box,
  Button,
  Center,
  Container,
  Group,
  Loader,
  Stack,
  Tabs,
  Text,
  Title,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAlertSquareRounded,
  IconArrowLeft,
  IconArrowsSplit2,
  IconClockPlay,
  IconCube,
} from '@tabler/icons-react';
import isEqual from 'lodash/isEqual';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { EventPluginTab } from './EventPluginTab';
import { InputPluginsTab } from './InputPluginsTab';
import { OutputPluginsTab } from './OutputPluginsTab';
import { FileTreeProvider } from './context/FileTreeContext';
import { ProjectNameProvider } from './context/ProjectNameContext';
import {
  useGeneratorConfig,
  useUpdateGeneratorConfigMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { GeneratorConfig } from '@/api/routes/generator-configs/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

export default function ProjectPage() {
  const { projectName } = useParams() as { projectName: string };
  const navigate = useNavigate();

  const [config, setConfig] = useState<GeneratorConfig>();

  const {
    data: generatorConfig,
    isSuccess: isGeneratorConfigSuccess,
    isError: isGeneratorConfigError,
    error: generatorConfigError,
    isLoading: isGeneratorConfigLoading,
  } = useGeneratorConfig(projectName);

  useEffect(() => {
    if (isGeneratorConfigSuccess) {
      setConfig({ ...generatorConfig });
    }
  }, [generatorConfig, isGeneratorConfigSuccess, setConfig]);

  const updateGeneratorConfig = useUpdateGeneratorConfigMutation();

  const hasUnsavedChanges = useMemo(() => {
    if (!isGeneratorConfigSuccess) {
      return false;
    }

    return !isEqual(generatorConfig, config);
  }, [generatorConfig, config, isGeneratorConfigSuccess]);

  function handleSave() {
    if (config === undefined) {
      return;
    }

    updateGeneratorConfig.mutate(
      { name: projectName, config: config },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: 'Project is saved',
            color: 'green',
          });
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to save project
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  function handleBack() {
    if (hasUnsavedChanges) {
      modals.openConfirmModal({
        title: 'Unsaved changes',
        children: (
          <Text size="sm">
            All unsaved changes in project <b>{projectName}</b> will be lost. Do
            you want to continue?
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Confirm' },
        onConfirm: () => void navigate(ROUTE_PATHS.PROJECTS),
      });
    } else {
      void navigate(ROUTE_PATHS.PROJECTS);
    }
  }

  if (isGeneratorConfigLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isGeneratorConfigError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to open project"
        >
          {generatorConfigError.message}
          <ShowErrorDetailsAnchor error={generatorConfigError} prependDot />
          <Anchor onClick={() => void navigate(ROUTE_PATHS.PROJECTS)}>
            <Text size="sm" ta="end">
              ← Go Back
            </Text>
          </Anchor>
        </Alert>
      </Container>
    );
  }

  if (isGeneratorConfigSuccess && config !== undefined) {
    return (
      <ProjectNameProvider initialProjectName={projectName}>
        <FileTreeProvider>
          <Container size="100%" mt="xs">
            <Stack>
              <Group justify="space-between">
                <Title order={3} fw="bold">
                  {projectName}
                </Title>
                <Group>
                  <Button
                    variant="default"
                    leftSection={<IconArrowLeft size={16} />}
                    onClick={handleBack}
                  >
                    Back
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={!hasUnsavedChanges}
                    loading={updateGeneratorConfig.isPending}
                    title={
                      hasUnsavedChanges
                        ? 'There are unsaved changes'
                        : 'No unsaved changes'
                    }
                  >
                    Save
                  </Button>
                </Group>
              </Group>
              <Tabs defaultValue="input" mt="lg">
                <Tabs.List>
                  <Tabs.Tab
                    value="input"
                    leftSection={<IconClockPlay size={14} />}
                  >
                    Input plugins
                  </Tabs.Tab>
                  <Tabs.Tab value="event" leftSection={<IconCube size={14} />}>
                    Event plugin
                  </Tabs.Tab>
                  <Tabs.Tab
                    value="output"
                    leftSection={<IconArrowsSplit2 size={14} />}
                  >
                    Output plugins
                  </Tabs.Tab>
                </Tabs.List>

                <Box mt="md">
                  <Tabs.Panel value="input">
                    <InputPluginsTab
                      initialInputPluginsConfig={generatorConfig.input}
                      onInputPluginsConfigChange={(config) =>
                        setConfig((prev) => ({ ...prev!, input: config }))
                      }
                    />
                  </Tabs.Panel>
                  <Tabs.Panel value="event">
                    <EventPluginTab
                      initialEventPluginConfig={generatorConfig.event}
                      onEventPluginConfigChange={(config) =>
                        setConfig((prev) => ({ ...prev!, event: config }))
                      }
                    />
                  </Tabs.Panel>
                  <Tabs.Panel value="output">
                    <OutputPluginsTab
                      initialOutputPluginsConfig={generatorConfig.output}
                      onOutputPluginsConfigChange={(config) =>
                        setConfig((prev) => ({ ...prev!, output: config }))
                      }
                    />
                  </Tabs.Panel>
                </Box>
              </Tabs>
            </Stack>
          </Container>
        </FileTreeProvider>
      </ProjectNameProvider>
    );
  }

  return <></>;
}
