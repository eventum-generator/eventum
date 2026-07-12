import {
  ActionIcon,
  Button,
  Code,
  Group,
  Text,
  Textarea,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconArrowsLeftRight,
  IconFileText,
  IconPlus,
  IconX,
} from '@tabler/icons-react';
import { nanoid } from 'nanoid';
import { FC, useState } from 'react';

import { useProjectName } from '../../hooks/useProjectName';
import {
  ToolBody,
  ToolEmpty,
  ToolPane,
  ToolShell,
  ToolSpacer,
} from '../../studio/panels/console/primitives';
import { FormatterParams } from '../OutputPluginParams/components/FormatterParams';
import { useFormatEventsMutation } from '@/api/hooks/usePreview';
import {
  Format,
  FormatterConfig,
} from '@/api/routes/generator-configs/schemas/plugins/output/formatters';
import { FormattingResult } from '@/api/routes/preview/schemas';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export const FormatterTab: FC = () => {
  const form = useForm<{ formatter?: FormatterConfig }>({
    initialValues: {
      formatter: {
        format: Format.Plain,
      },
    },
  });

  const { projectName } = useProjectName();
  const formatEvents = useFormatEventsMutation();

  const [events, setEvents] = useState<{ id: string; content: string }[]>([
    { id: nanoid(), content: '' },
  ]);
  const [formattingResult, setFormattingResult] =
    useState<FormattingResult | null>(null);

  function handleFormatEvents(values: typeof form.values) {
    if (values.formatter === undefined) {
      return;
    }

    formatEvents.mutate(
      {
        name: projectName,
        body: {
          events: events.map((event) => event.content),
          formatter_config: values.formatter,
        },
      },
      {
        onSuccess: (data) => {
          setFormattingResult(data);
        },
        onError: (error) => {
          notifications.show({
            title: 'Error',
            message: (
              <>
                Failed to format events
                <ShowErrorDetailsAnchor error={error} prependDot />
              </>
            ),
            color: 'red',
          });
        },
      }
    );
  }

  const canFormat = events.length > 0 && form.values.formatter !== undefined;

  return (
    <ToolShell
      toolbar={
        <>
          <Text size="xs" c="dimmed" maw={520}>
            Feed sample events through the configured formatter to preview the
            delivered payload.
          </Text>
          <ToolSpacer />
          <form onSubmit={form.onSubmit(handleFormatEvents)}>
            <Button
              size="xs"
              leftSection={<IconArrowsLeftRight size={15} />}
              type="submit"
              disabled={!canFormat}
              loading={formatEvents.isPending}
            >
              Format
            </Button>
          </form>
        </>
      }
    >
      <ToolBody>
        <ToolPane title="Formatter" grow={0} basis={300}>
          <FormatterParams
            value={form.values.formatter}
            onChange={(config) => {
              form.setFieldValue('formatter', config);
            }}
          />
        </ToolPane>

        <ToolPane
          title="Events"
          grow={1}
          actions={
            <Tooltip label="Add event" withArrow>
              <ActionIcon
                variant="default"
                size="sm"
                aria-label="Add event"
                onClick={() =>
                  setEvents((prev) => [...prev, { id: nanoid(), content: '' }])
                }
              >
                <IconPlus size={15} />
              </ActionIcon>
            </Tooltip>
          }
        >
          {events.length > 0 ? (
            <div className="tool-list">
              {events.map((event, index) => (
                <Textarea
                  key={event.id}
                  value={event.content}
                  placeholder="raw event ..."
                  minRows={2}
                  autosize
                  rightSection={
                    <ActionIcon
                      variant="subtle"
                      size="sm"
                      title="Delete event"
                      onClick={() => {
                        setEvents((prev) =>
                          prev.filter((e) => e.id !== event.id)
                        );
                      }}
                    >
                      <IconX size={15} />
                    </ActionIcon>
                  }
                  rightSectionProps={{
                    style: {
                      alignSelf: 'flex-start',
                      marginTop: 6,
                    },
                  }}
                  onChange={(e) => {
                    const next = [...events];
                    next[index] = { ...event, content: e.currentTarget.value };
                    setEvents(next);
                  }}
                />
              ))}
            </div>
          ) : (
            <ToolEmpty>Add an event to format.</ToolEmpty>
          )}
        </ToolPane>

        <ToolPane title="Result" grow={1}>
          {formattingResult === null ? (
            <ToolEmpty icon={<IconFileText size={28} />}>
              Format the events to preview the delivered output.
            </ToolEmpty>
          ) : (
            <>
              <Text size="xs" fw={600} c="dimmed" mb={6}>
                Formatted events
              </Text>
              {formattingResult.events.length > 0 ? (
                <div className="tool-list">
                  {formattingResult.events.map((event, index) => (
                    <Code key={index} block>
                      {event}
                    </Code>
                  ))}
                </div>
              ) : (
                <Text size="sm" c="dimmed">
                  No events
                </Text>
              )}

              <Group gap={6} mt="sm" mb={6}>
                <Text size="xs" fw={600} c="dimmed">
                  Errors
                </Text>
                {formattingResult.errors.length > 0 && (
                  <Text size="xs" c="var(--ev-bad)">
                    {formattingResult.errors.length}
                  </Text>
                )}
              </Group>
              {formattingResult.errors.length > 0 ? (
                <div className="tool-list">
                  {formattingResult.errors.map((error, index) => (
                    <Code key={index} block>
                      {error.message}
                      {error.original_event !== null &&
                        `\nOriginal event:\n${error.original_event}`}
                    </Code>
                  ))}
                </div>
              ) : (
                <Text size="sm" c="dimmed">
                  No errors
                </Text>
              )}
            </>
          )}
        </ToolPane>
      </ToolBody>
    </ToolShell>
  );
};
