import { CodeHighlight } from '@mantine/code-highlight';
import {
  Button,
  Center,
  Checkbox,
  Code,
  Divider,
  Group,
  NumberInput,
  Select,
  Stack,
  TagsInput,
  Text,
  TextInput,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconBug, IconBugOff, IconPlayerPlay } from '@tabler/icons-react';
import { FC, useState } from 'react';

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

export const DebuggerTab: FC = () => {
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

  const [isPluginInitialized, setPluginInitialized] = useState<boolean>(false);

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

  return (
    <Stack>
      <Group align="end" justify="space-between">
        <Group wrap="nowrap" align="start">
          <TextInput
            label={
              <LabelWithTooltip
                label="Event timestamp"
                tooltip="Timestamp from an input plugin. Note, that at actual runtime, timezone from generator settings will be used."
              />
            }
            rightSectionWidth="70px"
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
            label={
              <LabelWithTooltip
                label="Tags"
                tooltip="Tag list from an input plugin"
              />
            }
            placeholder="Press Enter to submit a tag"
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
            w="100px"
            {...produceParamsForm.getInputProps('eventsCount')}
          />
        </Group>
        <Group wrap="nowrap">
          {!isPluginInitialized && (
            <Button
              variant="default"
              title="Start debugging with new instance of event plugin"
              leftSection={<IconBug size={16} />}
              disabled={isPluginInitialized || produceEvents.isPending}
              loading={initializePlugin.isPending}
              onClick={handleStart}
            >
              Start
            </Button>
          )}
          {isPluginInitialized && (
            <Button
              variant="default"
              title="Stop debugging"
              leftSection={<IconBugOff size={16} />}
              disabled={!isPluginInitialized || produceEvents.isPending}
              loading={releasePlugin.isPending}
              onClick={handleStop}
            >
              Stop
            </Button>
          )}
          <Button
            variant="default"
            title="Produce event using provided parameters"
            leftSection={<IconPlayerPlay size={16} />}
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

      {producedEventsInfo !== undefined ? (
        <Stack gap="xs">
          <Stack gap="4px">
            <Text size="sm" fw="bold">
              Events
            </Text>
            <Divider />
          </Stack>
          <Select
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
            label="Syntax highlighting"
            maw="200px"
            clearable
          />
          {producedEventsInfo.events.length > 0 ? (
            producedEventsInfo.events.map((event, index) => (
              <CodeHighlight
                key={index}
                code={event}
                language={syntaxHighlighting ?? undefined}
                defaultExpanded
                withExpandButton
                collapseCodeLabel="Collapse"
                expandCodeLabel="Expand"
              />
            ))
          ) : (
            <Center>
              <Text size="sm" c="gray.6">
                No events
              </Text>
            </Center>
          )}

          <Stack gap="4px">
            <Text size="sm" fw="bold">
              Errors
            </Text>
            <Divider />
          </Stack>
          {producedEventsInfo.errors.length > 0 ? (
            producedEventsInfo.errors.map((error, index) => (
              <Code block key={index}>
                {`At event #${error.index + 1}: ${error.message} - ${error.context.reason ?? 'unknown reason'}\n\n`}
                {error.context.traceback ?? 'No traceback info\n\n'}

                {'\nAdditional context:\n'}
                {Object.entries(error.context)
                  .filter(([name]) => !['traceback', 'reason'].includes(name))
                  .map(([name, value]) => `- ${name}: ${value}\n`)}
              </Code>
            ))
          ) : (
            <Center>
              <Text size="sm" c="gray.6">
                No errors
              </Text>
            </Center>
          )}
        </Stack>
      ) : (
        <Stack gap="xs">
          <Divider />
          <Center>
            <Text size="sm" c="gray.6">
              No produced events
            </Text>
          </Center>
        </Stack>
      )}
    </Stack>
  );
};
