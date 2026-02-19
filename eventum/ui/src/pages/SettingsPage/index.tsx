import {
  Alert,
  Box,
  Center,
  Container,
  Grid,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { useEffect } from 'react';

import { GenerationParametersSection } from './GenerationParametersSection';
import { LoggingParametersSection } from './LoggingParametersSection';
import { PathParametersSection } from './PathParametersSection';
import { SavePanel } from './SavePanelContent';
import { ServerParametersSection } from './ServerParametersSection';
import {
  useInstanceSettings,
  useRestartInstanceMutation,
  useUpdateInstanceSettingsMutation,
} from '@/api/hooks/useInstance';
import {
  GenerationParameters,
  GenerationParametersSchema,
  LogParameters,
  LogParametersSchema,
  PathParameters,
  PathParametersSchema,
  ServerParameters,
  ServerParametersSchema,
  Settings,
} from '@/api/routes/instance/schemas';
import { FloatingPanel } from '@/components/ui/FloatingPanel';
import { FloatingTableOfContents } from '@/components/ui/FloatingTableOfContents';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function SettingsPage() {
  const ServerParamsForm = useForm<ServerParameters>({
    mode: 'uncontrolled',
    validate: zod4Resolver(ServerParametersSchema),
    validateInputOnChange: true,
  });
  const generationParamsForm = useForm<GenerationParameters>({
    mode: 'uncontrolled',
    validate: zod4Resolver(GenerationParametersSchema),
    validateInputOnChange: true,
    cascadeUpdates: true,
  });
  const logParamsForm = useForm<LogParameters>({
    mode: 'uncontrolled',
    validate: zod4Resolver(LogParametersSchema),
    validateInputOnChange: true,
  });
  const pathParamsForm = useForm<PathParameters>({
    mode: 'uncontrolled',
    validate: zod4Resolver(PathParametersSchema),
    validateInputOnChange: true,
  });

  const {
    data: instanceSettings,
    isLoading: isLoadingSettings,
    isSuccess: isSettingsSuccess,
    isError: isSettingsError,
    error: settingsError,
  } = useInstanceSettings();
  const updateInstanceSettings = useUpdateInstanceSettingsMutation();
  const restartInstance = useRestartInstanceMutation();

  useEffect(() => {
    if (isSettingsSuccess && !ServerParamsForm.initialized) {
      ServerParamsForm.initialize(instanceSettings.server);
      generationParamsForm.initialize(instanceSettings.generation);
      logParamsForm.initialize(instanceSettings.log);
      pathParamsForm.initialize(instanceSettings.path);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instanceSettings, isSettingsSuccess]);

  if (isLoadingSettings) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isSettingsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to get instance settings"
        >
          {settingsError.message}
          <ShowErrorDetailsAnchor error={settingsError} prependDot />
        </Alert>
      </Container>
    );
  }

  function handleSubmit() {
    const settings: Settings = {
      server: ServerParamsForm.getValues(),
      generation: generationParamsForm.getValues(),
      log: logParamsForm.getValues(),
      path: pathParamsForm.getValues(),
    };

    updateInstanceSettings.mutate(
      { settings: settings },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Success',
            message: 'Settings was successfully updated',
            color: 'green',
          });
          notifications.show({
            title: 'Info',
            message:
              'Restarting the instance. Service may be unavailable for some time',
            color: 'blue',
          });
          restartInstance.mutate(undefined, {
            onError: (error) => {
              notifications.show({
                title: 'Error',
                message: (
                  <>
                    Failed to restart instance.{' '}
                    <ShowErrorDetailsAnchor error={error} />
                  </>
                ),
                color: 'red',
              });
            },
          });
          ServerParamsForm.resetDirty();
          generationParamsForm.resetDirty();
          logParamsForm.resetDirty();
          pathParamsForm.resetDirty();
        },
        onError: (error: unknown) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to update settings
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  if (isSettingsSuccess && ServerParamsForm.initialized) {
    return (
      <>
        <Container size="xl" mb="600px">
          <Grid gutter="xl">
            <Grid.Col span="auto">
              <form>
                <Stack>
                  <PageTitle title="Settings" />
                  <Paper withBorder p="sm">
                    <Stack gap="xs">
                      <Title order={4} fw={500}>
                        Server parameters
                      </Title>
                      <ServerParametersSection form={ServerParamsForm} />
                    </Stack>
                  </Paper>

                  <Paper withBorder p="sm">
                    <Stack gap="xs">
                      <Title order={4} fw={500}>
                        Generation parameters
                      </Title>
                      <GenerationParametersSection
                        form={generationParamsForm}
                      />
                    </Stack>
                  </Paper>

                  <Paper withBorder p="sm">
                    <Stack gap="xs">
                      <Title order={4} fw={500}>
                        Path parameters
                      </Title>
                      <PathParametersSection form={pathParamsForm} />
                    </Stack>
                  </Paper>

                  <Paper withBorder p="sm">
                    <Stack gap="xs">
                      <Title order={4} fw={500}>
                        Logging parameters
                      </Title>
                      <LoggingParametersSection form={logParamsForm} />
                    </Stack>
                  </Paper>
                </Stack>

                <FloatingPanel
                  mounted={
                    ServerParamsForm.isDirty() ||
                    generationParamsForm.isDirty() ||
                    pathParamsForm.isDirty() ||
                    logParamsForm.isDirty()
                  }
                >
                  <SavePanel
                    onSave={() =>
                      modals.openConfirmModal({
                        title: 'Settings update',
                        children: (
                          <Text size="sm">
                            Instance will be restarted. Do you want to continue?
                          </Text>
                        ),
                        onConfirm: handleSubmit,
                        labels: { cancel: 'Cancel', confirm: 'Confirm' },
                      })
                    }
                  />
                </FloatingPanel>
              </form>
            </Grid.Col>

            <Grid.Col span={3}>
              <FloatingTableOfContents selector=":is(h4)" />
            </Grid.Col>
          </Grid>
        </Container>
      </>
    );
  }

  return null;
}
