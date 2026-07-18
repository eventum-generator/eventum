import { CodeHighlight } from '@mantine/code-highlight';
import {
  Button,
  Checkbox,
  Code,
  Group,
  NumberInput,
  Select,
  TagsInput,
  Text,
  TextInput,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconBug, IconBugOff, IconPlayerPlay } from '@tabler/icons-react';
import { FC, useState } from 'react';

import {
  ToolBody,
  ToolEmpty,
  ToolPane,
  ToolShell,
  ToolSpacer,
} from '../../../../studio/panels/console/primitives';
import { useGetPluginConfig } from '../../../hooks/useGetPluginConfig';
import {
  useInitializeEventPluginMutation,
  useProduceEventsMutation,
  useReleaseEventPluginMutation,
} from '@/api/hooks/usePreview';
import {
  ProduceParamsBody,
  ProducedEventsInfo,
} from '@/api/routes/preview/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { useProjectName } from '@/pages/ProjectPage/hooks/useProjectName';

interface DebuggerTabProps {
  /** Controlled plugin-initialized flag; lifted so sibling views (State) can
   *  gate on it and it survives view/stage switches. Falls back to internal
   *  state when used standalone. */
  initialized?: boolean;
  onInitializedChange?: (value: boolean) => void;
}

export const DebuggerTab: FC<DebuggerTabProps> = ({
  initialized,
  onInitializedChange,
}) => {
  const produceParamsForm = useForm<{
    timestamp: string;
    autoTimestamp: boolean;
    tags: string[];
    eventsCount: number;
  }>({
    initialValues: {
      timestamp: new Date().toISOString(),
      autoTimestamp: true,
      tags: [],
      eventsCount: 1,
    },
    validate: {
      timestamp: isNotEmpty('Timestamp is required'),
      eventsCount: isNotEmpty('Event count is required'),
    },
    validateInputOnBlur: true,
    onSubmitPreventDefault: 'always',
  });

  const { projectName } = useProjectName();
  const produceEvents = useProduceEventsMutation();

  const { getPluginConfig } = useGetPluginConfig();
  const initializePlugin = useInitializeEventPluginMutation();
  const releasePlugin = useReleaseEventPluginMutation();

  const [localInitialized, setLocalInitialized] = useState<boolean>(false);
  const isPluginInitialized = initialized ?? localInitialized;
  const setPluginInitialized = onInitializedChange ?? setLocalInitialized;

  const [producedEventsInfo, setProducedEventsInfo] =
    useState<ProducedEventsInfo>();

  const [syntaxHighlighting, setSyntaxHighlighting] = useState<string | null>(
    null
  );

  function handleStart() {
    const pluginConfig = getPluginConfig();
    initializePlugin.mutate(
      {
        name: projectName,
        eventPluginConfig: pluginConfig,
      },
      {
        onSuccess: () => {
          setPluginInitialized(true);
          notifications.show({
            title: 'Running',
            message: 'Plugin instance is running',
            color: 'blue',
          });
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to initialize plugin
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  function handleStop() {
    releasePlugin.mutate(
      {
        name: projectName,
      },
      {
        onSuccess: () => {
          setPluginInitialized(false);
          notifications.show({
            title: 'Stopped',
            message: 'Plugin instance is stopped',
            color: 'blue',
          });
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to stop plugin
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  function handleProduce() {
    const formValues = produceParamsForm.getValues();
    const produceParams: ProduceParamsBody = Array.from(
      { length: formValues.eventsCount },
      () => ({
        timestamp: formValues.timestamp,
        tags: formValues.tags,
      })
    );

    produceEvents.mutate(
      {
        name: projectName,
        produceParams: produceParams,
      },
      {
        onSuccess: (data) => {
          setProducedEventsInfo(data);

          if (data.exhausted) {
            notifications.show({
              title: 'Info',
              message: 'Plugin is exhausted',
              color: 'blue',
            });
          }

          if (produceParamsForm.getValues().autoTimestamp) {
            produceParamsForm.setFieldValue(
              'timestamp',
              new Date().toISOString()
            );
          }
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to produce events
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  const events = producedEventsInfo?.events ?? [];
  const errors = producedEventsInfo?.errors ?? [];

  return (
    <ToolShell
      toolbar={
        <>
          <TextInput
            w={250}
            label={
              <LabelWithTooltip
                label="Event timestamp"
                tooltip="Timestamp from an input plugin. Note, that at actual runtime, timezone from generator settings will be used."
              />
            }
            rightSectionWidth="62px"
            rightSection={
              <Checkbox
                label="Auto"
                labelPosition="left"
                size="xs"
                title="Auto increment timestamp on each event production"
                {...produceParamsForm.getInputProps('autoTimestamp', {
                  type: 'checkbox',
                })}
              />
            }
            {...produceParamsForm.getInputProps('timestamp')}
          />
          <TagsInput
            w={260}
            label={
              <LabelWithTooltip
                label="Tags"
                tooltip="Tag list from an input plugin"
              />
            }
            placeholder="Enter to add"
            styles={{ input: { maxHeight: 92, overflowY: 'auto' } }}
            {...produceParamsForm.getInputProps('tags')}
          />
          <NumberInput
            label={
              <LabelWithTooltip
                label="Count"
                tooltip="Number of event to generate with this parameters"
              />
            }
            placeholder="number"
            allowDecimal={false}
            min={1}
            max={100}
            w={90}
            {...produceParamsForm.getInputProps('eventsCount')}
          />
          <ToolSpacer />
          <Group gap="md" wrap="nowrap" className="tool-ctl">
            <Group gap={7} wrap="nowrap">
              <span className="tool-status-dot" data-on={isPluginInitialized} />
              <Text size="xs" c={isPluginInitialized ? undefined : 'dimmed'}>
                {isPluginInitialized ? 'Running' : 'Stopped'}
              </Text>
            </Group>
            <Group gap={8} wrap="nowrap">
              {isPluginInitialized ? (
                <Button
                  variant="default"
                  title="Stop debugging"
                  leftSection={<IconBugOff size={15} />}
                  disabled={produceEvents.isPending}
                  loading={releasePlugin.isPending}
                  onClick={handleStop}
                >
                  Stop
                </Button>
              ) : (
                <Button
                  variant="default"
                  title="Start debugging with new instance of event plugin"
                  leftSection={<IconBug size={15} />}
                  disabled={produceEvents.isPending}
                  loading={initializePlugin.isPending}
                  onClick={handleStart}
                >
                  Start
                </Button>
              )}
              <Button
                title="Produce event using provided parameters"
                leftSection={<IconPlayerPlay size={15} />}
                onClick={handleProduce}
                disabled={
                  !produceParamsForm.isValid() ||
                  !isPluginInitialized ||
                  initializePlugin.isPending ||
                  releasePlugin.isPending
                }
                loading={produceEvents.isPending}
              >
                Produce
              </Button>
            </Group>
          </Group>
        </>
      }
    >
      {producedEventsInfo === undefined ? (
        <ToolBody empty>
          <ToolEmpty icon={<IconBug size={28} />}>
            Start the plugin instance, then produce events to inspect the
            generated output and any errors.
          </ToolEmpty>
        </ToolBody>
      ) : (
        <ToolBody>
          <ToolPane
            title="Events"
            grow={1.5}
            actions={
              <Select
                w={140}
                placeholder="Syntax"
                data={[
                  'csv',
                  'json',
                  'log',
                  'markdown',
                  'toml',
                  'tsv',
                  'xml',
                  'yaml',
                ]}
                value={syntaxHighlighting}
                onChange={setSyntaxHighlighting}
                clearable
              />
            }
          >
            {events.length > 0 ? (
              <div className="tool-list">
                {events.map((event, index) => (
                  <CodeHighlight
                    key={index}
                    code={event}
                    language={syntaxHighlighting ?? undefined}
                    withCopyButton
                  />
                ))}
              </div>
            ) : (
              <ToolEmpty>No events produced for these parameters.</ToolEmpty>
            )}
          </ToolPane>
          <ToolPane title="Errors">
            {errors.length > 0 ? (
              <div className="tool-list">
                {errors.map((error, index) => (
                  <Code block key={index}>
                    {`At event #${error.index + 1}: ${error.message} - ${error.context.reason ?? 'unknown reason'}\n\n`}
                    {error.context.traceback ?? 'No traceback info\n\n'}

                    {'\nAdditional context:\n'}
                    {Object.entries(error.context)
                      .filter(
                        ([name]) => !['traceback', 'reason'].includes(name)
                      )
                      .map(([name, value]) => `- ${name}: ${value}\n`)}
                  </Code>
                ))}
              </div>
            ) : (
              <ToolEmpty>No errors.</ToolEmpty>
            )}
          </ToolPane>
        </ToolBody>
      )}
    </ToolShell>
  );
};
