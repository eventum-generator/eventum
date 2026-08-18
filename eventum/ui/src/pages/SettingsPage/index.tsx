import {
  Alert,
  Box,
  Button,
  Center,
  Container,
  Divider,
  Flex,
  Group,
  Loader,
  NavLink,
  Paper,
  Stack,
  Text,
  Title,
  Transition,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAdjustmentsHorizontal,
  IconFolders,
  IconLogs,
  IconServer2,
  type TablerIcon,
} from '@tabler/icons-react';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { useEffect, useState } from 'react';

import { GenerationParametersSection } from './GenerationParametersSection';
import { LoggingParametersSection } from './LoggingParametersSection';
import { PathParametersSection } from './PathParametersSection';
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
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { CONFIRM } from '@/theme/copy';

type SectionId = 'server' | 'generation' | 'path' | 'log';

interface SectionMeta {
  id: SectionId;
  label: string;
  icon: TablerIcon;
  description: string;
}

const SECTIONS: SectionMeta[] = [
  {
    id: 'server',
    label: 'Server',
    icon: IconServer2,
    description:
      'API, web UI, TLS, authentication and MCP access to this instance.',
  },
  {
    id: 'generation',
    label: 'Generation',
    icon: IconAdjustmentsHorizontal,
    description:
      'Defaults applied to every generator - ordering, batching and queues.',
  },
  {
    id: 'path',
    label: 'Paths',
    icon: IconFolders,
    description: 'Filesystem locations this instance reads from and writes to.',
  },
  {
    id: 'log',
    label: 'Logging',
    icon: IconLogs,
    description: 'Severity, format and rotation of this instance logs.',
  },
];

function initialSection(): SectionId {
  const hash = globalThis.location.hash.replace('#', '');
  return SECTIONS.some((s) => s.id === hash) ? (hash as SectionId) : 'server';
}

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

  const [activeSection, setActiveSection] = useState<SectionId>(initialSection);

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
          icon={<AlertIcon variant="error" />}
          title="Failed to get instance settings"
        >
          {settingsError.message}
          <ShowErrorDetailsAnchor error={settingsError} prependDot />
        </Alert>
      </Container>
    );
  }

  function selectSection(id: SectionId) {
    setActiveSection(id);
    globalThis.history.replaceState(null, '', `#${id}`);
  }

  function confirmSave() {
    modals.openConfirmModal({
      title: CONFIRM.restartInstance.title,
      children: <Text size="sm">{CONFIRM.restartInstance.body}</Text>,
      onConfirm: handleSubmit,
      labels: {
        cancel: CONFIRM.restartInstance.cancel,
        confirm: CONFIRM.restartInstance.confirm,
      },
    });
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
    const dirtyById: Record<SectionId, boolean> = {
      server: ServerParamsForm.isDirty(),
      generation: generationParamsForm.isDirty(),
      path: pathParamsForm.isDirty(),
      log: logParamsForm.isDirty(),
    };
    const anyDirty =
      dirtyById.server ||
      dirtyById.generation ||
      dirtyById.path ||
      dirtyById.log;
    const current = SECTIONS.find((s) => s.id === activeSection);
    if (!current) {
      return null;
    }

    return (
      <Container size="xl" mb="xl">
        <Stack gap="lg">
          <Box
            py="sm"
            style={{
              position: 'sticky',
              top: 60,
              zIndex: 30,
              background: 'var(--ev-canvas)',
              borderBottom: '1px solid var(--mantine-color-default-border)',
            }}
          >
            <Group
              justify="space-between"
              align="center"
              wrap="nowrap"
              mih={40}
            >
              <PageTitle title="Settings" />
              <Transition mounted={anyDirty} transition="pop" duration={150}>
                {(styles) => (
                  <Button onClick={confirmSave} style={styles}>
                    Save
                  </Button>
                )}
              </Transition>
            </Group>
          </Box>

          {/* The section list holds 230px and never shrinks, so side by side
              the form is left with whatever remains - below the breakpoint
              that is less than a single control needs. Stack them instead,
              and let the list scroll away with the page once it is on top. */}
          <Flex
            gap="xl"
            align="flex-start"
            direction={{ base: 'column', sm: 'row' }}
          >
            <Box
              w={{ base: '100%', sm: 230 }}
              pos={{ base: 'static', sm: 'sticky' }}
              top={128}
              style={{
                flexShrink: 0,
                alignSelf: 'flex-start',
              }}
            >
              <Stack gap={2}>
                {SECTIONS.map((section) => (
                  <NavLink
                    key={section.id}
                    label={section.label}
                    active={activeSection === section.id}
                    leftSection={<section.icon size={18} stroke={1.6} />}
                    rightSection={
                      dirtyById[section.id] ? (
                        <Box
                          w={7}
                          h={7}
                          bdrs={999}
                          bg="var(--mantine-color-primary-text)"
                          aria-label="unsaved changes"
                        />
                      ) : null
                    }
                    onClick={() => selectSection(section.id)}
                    style={{ borderRadius: 'var(--mantine-radius-md)' }}
                  />
                ))}
              </Stack>
            </Box>

            <Box style={{ flex: 1, minWidth: 0, maxWidth: 820 }}>
              <Paper withBorder p="lg">
                <Stack gap="md">
                  <Box>
                    <Title order={3} fw={600} fz="1.125rem">
                      {current.label}
                    </Title>
                    <Text size="sm" c="dimmed" mt={4}>
                      {current.description}
                    </Text>
                  </Box>
                  <Divider />

                  {activeSection === 'server' && (
                    <ServerParametersSection form={ServerParamsForm} />
                  )}
                  {activeSection === 'generation' && (
                    <GenerationParametersSection form={generationParamsForm} />
                  )}
                  {activeSection === 'path' && (
                    <PathParametersSection form={pathParamsForm} />
                  )}
                  {activeSection === 'log' && (
                    <LoggingParametersSection form={logParamsForm} />
                  )}
                </Stack>
              </Paper>
            </Box>
          </Flex>
        </Stack>
      </Container>
    );
  }

  return null;
}
