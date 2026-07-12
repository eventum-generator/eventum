import {
  Alert,
  Box,
  Center,
  Container,
  Loader,
  Stack,
  Tabs,
  Text,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import {
  IconAlertSquareRounded,
  IconGauge,
  IconLayoutDashboard,
  IconLogs,
  IconSettings,
} from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { dirname } from 'pathe';
import { useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { InstanceHeader } from './InstanceHeader';
import { LogsTab } from './tabs/LogsTab';
import { MetricsTab } from './tabs/MetricsTab';
import { OverviewTab } from './tabs/OverviewTab';
import { SettingsTab } from './tabs/SettingsTab';
import {
  useGenerator,
  useGeneratorStatus,
  useStartGeneratorMutation,
  useStopGeneratorMutation,
  useUpdateGeneratorMutation,
} from '@/api/hooks/useGenerators';
import { useScenarios } from '@/api/hooks/useScenarios';
import {
  useStartupGenerator,
  useUpdateGeneratorInStartupMutation,
} from '@/api/hooks/useStartup';
import { GeneratorParametersSchema } from '@/api/routes/generators/schemas';
import {
  StartupGeneratorParameters,
  StartupGeneratorParametersSchema,
} from '@/api/routes/startup/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

const TABS = new Set(['overview', 'metrics', 'logs', 'settings']);

export default function InstancePage() {
  const { instanceId } = useParams() as { instanceId: string };
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const tab = searchParams.get('tab') ?? 'overview';
  const activeTab = TABS.has(tab) ? tab : 'overview';

  function setTab(value: string | null) {
    setSearchParams(
      (prev) => {
        prev.set('tab', value ?? 'overview');
        return prev;
      },
      { replace: true }
    );
  }

  const {
    data: status,
    isLoading: isStatusLoading,
    isError: isStatusError,
    isSuccess: isStatusSuccess,
    error: statusError,
  } = useGeneratorStatus(instanceId, { refetchInterval: 4000 });

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

  const { data: allScenarios } = useScenarios();

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
      // Scenarios membership is managed separately (immediate add/remove);
      // the form carries the initial value only to satisfy its type - no
      // form input edits it, and saving re-reads the live value.
      form.initialize({
        ...generatorParams,
        autostart: startupGeneratorParams.autostart,
        scenarios: startupGeneratorParams.scenarios ?? [],
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
  const stopGenerator = useStopGeneratorMutation();
  const startGenerator = useStartGeneratorMutation();

  function buildStartupParams(): StartupGeneratorParameters {
    // Preserve current scenario membership from the query, never the form.
    return {
      ...form.getValues(),
      scenarios: startupGeneratorParams?.scenarios ?? [],
    };
  }

  function persist(afterSave?: () => void) {
    const params = GeneratorParametersSchema.parse(form.getValues());
    const startupParams = buildStartupParams();

    updateGenerator.mutate(
      { id: instanceId, params },
      {
        onSuccess: () => {
          updateGeneratorInStartup.mutate(
            { id: instanceId, params: startupParams },
            {
              onSuccess: () => {
                form.resetDirty();
                showSuccessNotification('Success', 'Instance is saved');
                afterSave?.();
              },
              onError: (error) =>
                showErrorNotification('Failed to save instance', error),
            }
          );
        },
        onError: (error) =>
          showErrorNotification('Failed to save instance', error),
      }
    );
  }

  function handleSave() {
    if (form.validate().hasErrors) {
      return;
    }

    if (status?.is_initializing || status?.is_running) {
      modals.openConfirmModal({
        title: 'Updating instance',
        children: (
          <Text size="sm">
            Instance <b>{instanceId}</b> is currently running. It will be
            restarted for saving changes. Do you want to continue?
          </Text>
        ),
        labels: { cancel: 'Cancel', confirm: 'Confirm' },
        onConfirm: () =>
          stopGenerator.mutate(
            { id: instanceId },
            {
              onSuccess: () =>
                persist(() =>
                  startGenerator.mutate(
                    { id: instanceId },
                    {
                      onSuccess: () =>
                        showSuccessNotification(
                          'Success',
                          'Instance is started'
                        ),
                      onError: (error) =>
                        showErrorNotification(
                          'Failed to start instance',
                          error
                        ),
                    }
                  )
                ),
              onError: (error) =>
                showErrorNotification('Failed to stop instance', error),
            }
          ),
      });
    } else {
      persist();
    }
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

  const loadError = isGeneratorParamsError
    ? {
        title: 'Failed to get instance parameters',
        error: generatorParamsError,
      }
    : isStartupGeneratorParamsError
      ? {
          title: 'Failed to get startup instance parameters',
          error: startupGeneratorParamsError,
        }
      : isStatusError
        ? { title: 'Failed to get instance status', error: statusError }
        : null;

  if (loadError) {
    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded} />}
          title={loadError.title}
        >
          {loadError.error?.message}
          {loadError.error && (
            <ShowErrorDetailsAnchor error={loadError.error} prependDot />
          )}
        </Alert>
      </Container>
    );
  }

  if (
    !generatorParams ||
    !startupGeneratorParams ||
    !status ||
    !isGeneratorParamsSuccess ||
    !isStatusSuccess ||
    !form.initialized
  ) {
    return null;
  }

  const liveMode = generatorParams.live_mode ?? false;
  const autostart = startupGeneratorParams.autostart ?? false;
  const memberScenarios = startupGeneratorParams.scenarios ?? [];
  const isDirty = form.isDirty();
  const isSaving =
    updateGenerator.isPending ||
    updateGeneratorInStartup.isPending ||
    stopGenerator.isPending ||
    startGenerator.isPending;

  return (
    <Container size="100%">
      <Stack gap="lg">
        <InstanceHeader
          instanceId={instanceId}
          status={status}
          projectName={dirname(generatorParams.path)}
          liveMode={liveMode}
          autostart={autostart}
          isDirty={isDirty}
          isSaving={isSaving}
          onSave={handleSave}
          onBack={handleBack}
        />

        <Tabs value={activeTab} onChange={setTab} keepMounted={false}>
          <Tabs.List>
            <Tabs.Tab
              value="overview"
              leftSection={<IconLayoutDashboard size={16} />}
            >
              Overview
            </Tabs.Tab>
            <Tabs.Tab value="metrics" leftSection={<IconGauge size={16} />}>
              Metrics
            </Tabs.Tab>
            <Tabs.Tab value="logs" leftSection={<IconLogs size={16} />}>
              Logs
            </Tabs.Tab>
            <Tabs.Tab
              value="settings"
              leftSection={<IconSettings size={16} />}
              rightSection={
                isDirty ? (
                  <Box
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      background: 'var(--ev-accent)',
                    }}
                  />
                ) : null
              }
            >
              Settings
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="overview" pt="lg">
            <OverviewTab
              instanceId={instanceId}
              status={status}
              generatorParams={generatorParams}
              liveMode={liveMode}
              autostart={autostart}
              memberScenarios={memberScenarios}
              allScenarios={allScenarios ?? []}
            />
          </Tabs.Panel>
          <Tabs.Panel value="metrics" pt="lg">
            <MetricsTab instanceId={instanceId} />
          </Tabs.Panel>
          <Tabs.Panel value="logs" pt="lg">
            <LogsTab instanceId={instanceId} />
          </Tabs.Panel>
          <Tabs.Panel value="settings" pt="lg">
            <SettingsTab form={form} />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
