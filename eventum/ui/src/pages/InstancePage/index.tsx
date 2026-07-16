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
  IconLayoutDashboard,
  IconLogs,
  IconSettings,
} from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { InstanceHeader } from './InstanceHeader';
import { useInstanceHistory } from './dashboard/useInstanceHistory';
import { LogsTab } from './tabs/LogsTab';
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
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { UnsavedChangesPrompt } from '@/components/ui/UnsavedChangesPrompt';
import { ROUTE_PATHS } from '@/routing/paths';
import { CONFIRM } from '@/theme/copy';
import {
  showErrorNotification,
  showSuccessNotification,
} from '@/utils/notifications';

const TABS = new Set(['overview', 'logs', 'settings']);

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

  // Poll live stats + accumulate throughput history at the page shell (not the
  // Overview panel) so the graph keeps its points across tab switches.
  const {
    stats: liveStats,
    flow,
    inputEps,
    outputEps,
  } = useInstanceHistory(instanceId, status?.is_running ?? false);

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
        title: CONFIRM.restartInstance.title,
        children: <Text size="sm">{CONFIRM.restartInstance.body}</Text>,
        labels: {
          cancel: CONFIRM.restartInstance.cancel,
          confirm: CONFIRM.restartInstance.confirm,
        },
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

  // Leaving with unsaved changes is guarded globally by UnsavedChangesPrompt
  // (covers the sidebar and every other navigation, not just this button).
  function handleBack() {
    void navigate(ROUTE_PATHS.INSTANCES);
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
          icon={<AlertIcon variant="error" />}
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
        <UnsavedChangesPrompt when={isDirty} />
        <InstanceHeader
          instanceId={instanceId}
          status={status}
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
            <Tabs.Tab value="logs" leftSection={<IconLogs size={16} />}>
              Logs
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="overview" pt="lg">
            <OverviewTab
              instanceId={instanceId}
              status={status}
              generatorParams={generatorParams}
              liveMode={liveMode}
              autostart={startupGeneratorParams.autostart ?? false}
              memberScenarios={memberScenarios}
              allScenarios={allScenarios ?? []}
              stats={liveStats}
              flow={flow}
              inputEps={inputEps}
              outputEps={outputEps}
            />
          </Tabs.Panel>
          <Tabs.Panel value="settings" pt="lg">
            <SettingsTab form={form} />
          </Tabs.Panel>
          <Tabs.Panel value="logs" pt="lg">
            <LogsTab instanceId={instanceId} />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
