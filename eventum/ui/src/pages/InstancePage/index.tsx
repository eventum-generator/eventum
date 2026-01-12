import {
  Alert,
  Box,
  Button,
  Center,
  Checkbox,
  Container,
  Divider,
  Group,
  JsonInput,
  Loader,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { UseFormReturnType, useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconAlertSquareRounded, IconArrowLeft } from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { GenerationParametersSection } from '../SettingsPage/GenerationParametersSection';
import {
  useGenerator,
  useGeneratorStatus,
  useStartGeneratorMutation,
  useStopGeneratorMutation,
  useUpdateGeneratorMutation,
} from '@/api/hooks/useGenerators';
import {
  useStartupGenerator,
  useUpdateGeneratorInStartupMutation,
} from '@/api/hooks/useStartup';
import { GeneratorParametersSchema } from '@/api/routes/generators/schemas';
import { GenerationParameters } from '@/api/routes/instance/schemas';
import {
  StartupGeneratorParameters,
  StartupGeneratorParametersSchema,
} from '@/api/routes/startup/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

export default function InstancePage() {
  const { instanceId } = useParams() as { instanceId: string };
  const navigate = useNavigate();

  const {
    data: status,
    isLoading: isStatusLoading,
    isError: isStatusError,
    isSuccess: isStatusSuccess,
    error: statusError,
  } = useGeneratorStatus(instanceId);

  const {
    data: generatorParams,
    isLoading: isGeneratorParamsLoading,
    isError: isGeneratorParamsError,
    error: generatorParamsError,
    isSuccess: isGeneratorParamsSuccess,
  } = useGenerator(instanceId);

  const {
    data: startupGeneratorParams,
    isLoading: isStartupGeneratorParamsLoading,
    isError: isStartupGeneratorParamsError,
    error: startupGeneratorParamsError,
    isSuccess: isStartupGeneratorParamsSuccess,
  } = useStartupGenerator(instanceId);

  const form = useForm<StartupGeneratorParameters>({
    mode: 'uncontrolled',
    validate: zod4Resolver(StartupGeneratorParametersSchema),
    validateInputOnChange: true,
    cascadeUpdates: true,
  });

  useEffect(() => {
    if (
      isGeneratorParamsSuccess &&
      isStartupGeneratorParamsSuccess &&
      !form.initialized
    ) {
      form.initialize({
        ...generatorParams,
        autostart: startupGeneratorParams.autostart,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    generatorParams,
    isGeneratorParamsSuccess,
    startupGeneratorParams,
    isStartupGeneratorParamsSuccess,
  ]);

  const updateGenerator = useUpdateGeneratorMutation();
  const updateGeneratorInStartup = useUpdateGeneratorInStartupMutation();

  function handleSave() {
    const generatorParams = GeneratorParametersSchema.parse(form.getValues());
    const startupGeneratorParams = form.getValues();

    updateGenerator.mutate(
      { id: instanceId, params: generatorParams },
      {
        onSuccess: () => {
          updateGeneratorInStartup.mutate(
            { id: instanceId, params: startupGeneratorParams },
            {
              onSuccess: () => {
                form.resetDirty();
                notifications.show({
                  title: 'Success',
                  message: 'Instance is saved',
                  color: 'green',
                });
              },
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to save instance
                      <ShowErrorDetailsAnchor error={error} prependDot />
                    </>
                  ),
                  color: 'red',
                });
              },
            }
          );
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to save instance
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  const stopGenerator = useStopGeneratorMutation();
  const startGenerator = useStartGeneratorMutation();

  function handleSaveWithRestart() {
    const params = GeneratorParametersSchema.parse(form.getValues());
    const startupGeneratorParams = form.getValues();

    stopGenerator.mutate(
      { id: instanceId },
      {
        onSuccess: () => {
          updateGenerator.mutate(
            { id: instanceId, params: params },
            {
              onSuccess: () => {
                updateGeneratorInStartup.mutate(
                  { id: instanceId, params: startupGeneratorParams },
                  {
                    onSuccess: () => {
                      form.resetDirty();
                      notifications.show({
                        title: 'Success',
                        message: 'Instance is saved',
                        color: 'green',
                      });
                      startGenerator.mutate(
                        { id: instanceId },
                        {
                          onSuccess: () => {
                            notifications.show({
                              title: 'Success',
                              message: 'Instance is started',
                              color: 'green',
                            });
                          },
                          onError: (error) => {
                            notifications.show({
                              title: 'Error',
                              message: (
                                <>
                                  Failed to start instance
                                  <ShowErrorDetailsAnchor
                                    error={error}
                                    prependDot
                                  />
                                </>
                              ),
                              color: 'red',
                            });
                          },
                        }
                      );
                    },
                    onError: (error) => {
                      notifications.show({
                        title: 'Error',
                        message: (
                          <>
                            Failed to save instance
                            <ShowErrorDetailsAnchor error={error} prependDot />
                          </>
                        ),
                        color: 'red',
                      });
                    },
                  }
                );
              },
              onError: (error) => {
                notifications.show({
                  title: 'Error',
                  message: (
                    <>
                      Failed to save instance
                      <ShowErrorDetailsAnchor error={error} prependDot />
                    </>
                  ),
                  color: 'red',
                });
              },
            }
          );
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to stop instance
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
    if (form.isDirty()) {
      modals.openConfirmModal({
        title: 'Unsaved changes',
        children: (
          <Text size="sm">
            All unsaved changes in instance <b>{instanceId}</b> will be lost. Do
            you want to continue?
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Confirm' },
        onConfirm: () => void navigate(ROUTE_PATHS.INSTANCES),
      });
    } else {
      void navigate(ROUTE_PATHS.INSTANCES);
    }
  }

  if (
    isGeneratorParamsLoading ||
    isStartupGeneratorParamsLoading ||
    isStatusLoading
  ) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isGeneratorParamsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to get instance parameters"
        >
          {generatorParamsError.message}
          <ShowErrorDetailsAnchor error={generatorParamsError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isStartupGeneratorParamsError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to get startup instance parameters"
        >
          {startupGeneratorParamsError.message}
          <ShowErrorDetailsAnchor
            error={startupGeneratorParamsError}
            prependDot
          />
        </Alert>
      </Container>
    );
  }

  if (isStatusError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to get instance status"
        >
          {statusError.message}
          <ShowErrorDetailsAnchor error={statusError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isGeneratorParamsSuccess && isStatusSuccess && form.initialized) {
    return (
      <Container size="100%" mt="xs">
        <Stack>
          <Group justify="space-between">
            <Title order={3} fw="bold">
              {instanceId}
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
                onClick={() => {
                  if (status.is_initializing || status.is_running) {
                    modals.openConfirmModal({
                      title: 'Updating instance',
                      children: (
                        <Text size="sm">
                          Instance <b>{instanceId}</b> is currently running. It
                          will be restarted for saving changes. Do you want to
                          continue?
                        </Text>
                      ),
                      labels: { cancel: 'Cancel', confirm: 'Confirm' },
                      onConfirm: handleSaveWithRestart,
                    });
                  } else {
                    handleSave();
                  }
                }}
                disabled={!form.isDirty()}
                loading={
                  updateGenerator.isPending ||
                  updateGeneratorInStartup.isPending ||
                  stopGenerator.isPending ||
                  startGenerator.isPending
                }
                title={
                  form.isDirty()
                    ? 'There are unsaved changes'
                    : 'No unsaved changes'
                }
              >
                Save
              </Button>
            </Group>
          </Group>

          <Stack gap="4px">
            <Title order={4} fw={500} mt="xl">
              Generator parameters
            </Title>
            <Divider />
          </Stack>

          <Group>
            <Switch
              label={
                <LabelWithTooltip
                  label="Live mode"
                  tooltip="Whether to use live mode and generate events at moments defined by timestamp
                values or sample mode to generate all events at a time"
                />
              }
              {...form.getInputProps('live_mode', { type: 'checkbox' })}
            />
            <Switch
              label={
                <LabelWithTooltip
                  label="Skip past"
                  tooltip="Whether to skip past timestamps when starting generation in live mode"
                />
              }
              {...form.getInputProps('skip_past', { type: 'checkbox' })}
            />
            <Checkbox
              label={
                <LabelWithTooltip
                  label="Auto start"
                  tooltip="Whether to automatically start the generator on application start up"
                />
              }
              {...form.getInputProps('autostart', { type: 'checkbox' })}
            />
          </Group>

          <JsonInput
            label="Parameters"
            description="Parameters that can be used in generator configuration file"
            placeholder="{ ... }"
            validationError="Invalid JSON"
            minRows={4}
            autosize
            defaultValue={JSON.stringify(
              form.getValues().params ?? '',
              undefined,
              2
            )}
            onChange={(value) => {
              if (value === '') {
                form.setFieldValue('params', undefined);
              }

              let parsedValue: unknown;
              try {
                parsedValue = JSON.parse(value);
              } catch {
                return;
              }

              if (typeof parsedValue !== 'object') {
                return;
              }

              form.setFieldValue(
                'params',
                parsedValue as Record<string, unknown>
              );
            }}
            error={form.errors.params}
          />

          <Stack gap="4px">
            <Title order={4} fw={500} mt="xl">
              Generation parameters
            </Title>
            <Divider />
          </Stack>

          <GenerationParametersSection
            form={form as unknown as UseFormReturnType<GenerationParameters>}
          />
        </Stack>
      </Container>
    );
  }

  return null;
}
