import {
  ActionIcon,
  Button,
  Center,
  Code,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconArrowsLeftRight, IconPlus, IconX } from '@tabler/icons-react';
import { nanoid } from 'nanoid';
import { FC, useState } from 'react';

import { useProjectName } from '../../hooks/useProjectName';
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
    <Stack gap="xs">
      <FormatterParams
        value={form.values.formatter}
        onChange={(config) => {
          form.setFieldValue('formatter', config);
        }}
      />

      <Stack gap="2px">
        <Group justify="space-between">
          <Text size="sm" fw="bold">
            Events
          </Text>
          <form onSubmit={form.onSubmit(handleFormatEvents)}>
            <Button
              variant="transparent"
              c={canFormat ? 'primary' : 'gray.6'}
              leftSection={<IconArrowsLeftRight size={16} />}
              type="submit"
              disabled={!canFormat}
              loading={formatEvents.isPending}
            >
              Format
            </Button>
          </form>
          <Text size="sm" fw="bold">
            Result
          </Text>
        </Group>
        <Divider />
      </Stack>

      <Group grow align="start">
        <Stack gap="xs">
          {events.map((event, index) => (
            <Textarea
              key={event.id}
              value={event.content}
              placeholder="..."
              minRows={2}
              autosize
              rightSection={
                <ActionIcon
                  variant="transparent"
                  size="sm"
                  title="Delete event"
                  onClick={() => {
                    setEvents((prev) => prev.filter((e) => e.id !== event.id));
                  }}
                >
                  <IconX size={16} />
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

          <Button
            variant="default"
            leftSection={<IconPlus size={16} />}
            onClick={() => {
              setEvents((prev) => [...prev, { id: nanoid(), content: '' }]);
            }}
          >
            Add
          </Button>
        </Stack>

        <Stack gap="xs">
          {formattingResult !== null ? (
            <Stack gap="xs">
              <Paper withBorder p="xs">
                <Stack gap="4px">
                  <Text size="sm" fw="bold">
                    Formatted events
                  </Text>
                  {formattingResult.events.length === 0 && (
                    <Center>
                      <Text size="sm" c="gray.6">
                        No events
                      </Text>
                    </Center>
                  )}
                  <Stack gap="xs">
                    {formattingResult.events.map((event, index) => (
                      <Code key={index} block>
                        {event}
                      </Code>
                    ))}
                  </Stack>
                </Stack>
              </Paper>

              <Paper withBorder p="xs">
                <Stack gap="4px">
                  <Text size="sm" fw="bold">
                    Errors
                  </Text>
                  {formattingResult.errors.length === 0 && (
                    <Center>
                      <Text size="sm" c="gray.6">
                        No errors
                      </Text>
                    </Center>
                  )}
                  <Stack gap="xs">
                    {formattingResult.errors.map((error, index) => (
                      <Code key={index} block>
                        {error.message}
                        {error.original_event !== null &&
                          `\nOriginal event:\n${error.original_event}`}
                      </Code>
                    ))}
                  </Stack>
                </Stack>
              </Paper>
            </Stack>
          ) : (
            <Center>
              <Text c="gray.6" size="sm">
                No result
              </Text>
            </Center>
          )}
        </Stack>
      </Group>
    </Stack>
  );
};
