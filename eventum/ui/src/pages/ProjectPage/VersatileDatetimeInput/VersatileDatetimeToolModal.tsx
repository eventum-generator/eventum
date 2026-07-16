import {
  Alert,
  Button,
  Code,
  Divider,
  Group,
  List,
  Radio,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { FC, useState } from 'react';

import { useProjectName } from '../hooks/useProjectName';
import { APIError } from '@/api/errors';
import { useNormalizedVersatileDatetimeMutation } from '@/api/hooks/usePreview';
import { VersatileDatetimeParametersBody } from '@/api/routes/preview/schemas';
import { TIMEZONES } from '@/api/schemas/timezones';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export const VersatileDatetimeToolModal: FC = () => {
  const { projectName } = useProjectName();

  const form = useForm<VersatileDatetimeParametersBody>({
    initialValues: {
      value: '',
      timezone: 'UTC',
      none_point: 'now',
    },
    onSubmitPreventDefault: 'always',
    validateInputOnChange: true,
    transformValues: (values) => {
      if (values.value === '') {
        values.value = null;
      }
      if (values.relative_base === '') {
        values.relative_base = null;
      }
      return values;
    },
  });

  const normalizeDatetime = useNormalizedVersatileDatetimeMutation();

  const [normalizedDatetime, setNormalizedValue] = useState<string | null>(
    null
  );
  const [normalizationError, setNormalizationError] = useState<string | null>(
    null
  );

  function handleNormalizeDatetime(values: typeof form.values) {
    normalizeDatetime.mutate(
      {
        name: projectName,
        parameters: values,
      },
      {
        onSuccess: (normalizedDatetime) => {
          setNormalizedValue(normalizedDatetime);
          setNormalizationError(null);
        },
        onError: (error) => {
          if (
            error instanceof APIError &&
            (error.response?.status === 400 || error.response?.status === 422)
          ) {
            setNormalizedValue(null);
            setNormalizationError('Expression is invalid');
          } else {
            notifications.show({
              title: 'Error',
              message: (
                <>
                  Failed to normalize value.{' '}
                  <ShowErrorDetailsAnchor error={error} />
                </>
              ),
              color: 'red',
            });
          }
        },
      }
    );
  }

  return (
    <Stack>
      <Text size="sm">
        Across all input plugins it is possible to specify time in{' '}
        <b>versatile datetime format</b>.
      </Text>

      <Stack gap="0">
        <Text size="sm">This format supports:</Text>
        <List size="sm">
          <List.Item>
            Datetime expressions (as Unix timestamp or ISO8601 string, e.g.{' '}
            <Code>1735678800</Code>, <Code>1763408275.769</Code>,{' '}
            <Code>1763408275769</Code>,{' '}
            <Code>2025-01-01T00:00:00.000000+00:00</Code>,{' '}
            <Code>2025-01-01 00:00</Code>)
          </List.Item>
          <List.Item>
            Time expressions (e.g <Code>12:35</Code>, <Code>09:00</Code>,{' '}
            <Code>23:50</Code>)
          </List.Item>
          <List.Item>
            Time keywords (<Code>now</Code> or <Code>never</Code>)
          </List.Item>
          <List.Item>
            Relative time expressions (e.g. <Code>+1h</Code>, <Code>-15m</Code>,{' '}
            <Code>+1d12h30m15s</Code>)
          </List.Item>
          <List.Item>
            Human-friendly expressions (e.g. <Code>1 min ago</Code>,{' '}
            <Code>2 weeks ago</Code>,{' '}
            <Code>3 months, 1 week and 1 day ago</Code>, <Code>in 2 days</Code>,{' '}
            <Code>tomorrow</Code>, <Code>1st.</Code>,{' '}
            <Code>August 14, 2015 EST</Code>, <Code>Monday</Code>)
          </List.Item>
        </List>
      </Stack>
      <Text size="sm">
        Below you can test your expression and see normalized value.
      </Text>
      <Divider />

      <form onSubmit={form.onSubmit(handleNormalizeDatetime)}>
        <Stack>
          <TextInput
            label="Value"
            placeholder="time expression"
            {...form.getInputProps('value', { type: 'input' })}
          />
          <Select
            label={
              <LabelWithTooltip
                label="Timezone"
                tooltip="Timezone that will be used in normalized datetime"
              />
            }
            data={TIMEZONES}
            searchable
            nothingFoundMessage="No timezones matched"
            placeholder="zone name"
            {...form.getInputProps('timezone', {
              type: 'input',
            })}
          />
          <TextInput
            label={
              <LabelWithTooltip
                label="Relative base"
                tooltip="Base time to use when value represents relative time, default is the current time"
              />
            }
            placeholder="datetime (unix timestamps or ISO8601 string)"
            {...form.getInputProps('relative_base', { type: 'input' })}
          />
          <Radio.Group
            name="nonePoint"
            label="None point"
            description="What time to use when value is not set. Most of the input plugins use `now` for start and `max` for end time of generation if value is not set."
            {...form.getInputProps('none_point', { type: 'input' })}
          >
            <Group mt="xs">
              <Radio value="now" label="Now" />
              <Radio value="min" label="Min" />
              <Radio value="max" label="Max" />
            </Group>
          </Radio.Group>

          <Button type="submit" loading={normalizeDatetime.isPending}>
            Normalize
          </Button>
        </Stack>
      </form>

      {normalizationError !== null ? (
        <Alert
          variant="default"
          title="Invalid"
          icon={<AlertIcon variant="error" />}
        >
          {normalizationError}
        </Alert>
      ) : (
        <></>
      )}

      {normalizedDatetime !== null ? (
        <Alert
          variant="default"
          title="Valid"
          icon={<AlertIcon variant="success" />}
        >
          Expression is valid: <Code>{normalizedDatetime}</Code>
        </Alert>
      ) : (
        <></>
      )}
    </Stack>
  );
};
