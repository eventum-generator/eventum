import {
  Alert,
  Box,
  Group,
  NumberInput,
  Paper,
  Radio,
  Select,
  Stack,
  Switch,
  Text,
  Tooltip,
} from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { IconInfoCircle } from '@tabler/icons-react';
import { FC, useState } from 'react';

import { QueueSizeApproximation } from './QueueSizeApproximation';
import { GenerationParameters } from '@/api/routes/instance/schemas';
import { TIMEZONES } from '@/api/schemas/timezones';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface GenerationParametersSectionProps {
  form: UseFormReturnType<GenerationParameters>;
}

export const GenerationParametersSection: FC<
  GenerationParametersSectionProps
> = ({ form }) => {
  const formValues = form.getValues();
  const [batchingMode, setBatchingMode] = useState<
    'size' | 'delay' | 'combined'
  >(
    formValues?.batch?.size && formValues?.batch?.delay
      ? 'combined'
      : formValues?.batch?.size
        ? 'delay'
        : 'size'
  );

  const [batchSize, setBatchSize] = useState(formValues?.batch?.size);
  const [queueParams, setQueueParams] = useState(formValues.queue);

  form.watch('batch.size', ({ value }) => {
    setBatchSize(value);
  });
  form.watch('queue', ({ value }) => {
    setQueueParams(value);
  });

  return (
    <Stack gap="xs">
      <Switch
        label={
          <LabelWithTooltip
            label="Keep events order"
            tooltip="Whether to keep chronological order of events using their timestamps by disabling output plugins concurrency"
          />
        }
        {...form.getInputProps('keep_order', {
          type: 'checkbox',
        })}
        key={form.key('keep_order')}
      />
      <Select
        label={
          <LabelWithTooltip
            label="Timezone"
            tooltip="Time zone for generating timestamps"
          />
        }
        data={TIMEZONES}
        searchable
        nothingFoundMessage="No timezones matched"
        placeholder="zone name"
        {...form.getInputProps('timezone')}
        key={form.key('timezone')}
      />
      <NumberInput
        label={
          <LabelWithTooltip
            label="Maximum concurrent writes"
            tooltip="Maximum number of write operations performed by output plugins concurrently"
          />
        }
        placeholder="number"
        min={1}
        allowDecimal={false}
        {...form.getInputProps('max_concurrency')}
        key={form.key('max_concurrency')}
      />
      <NumberInput
        label={
          <LabelWithTooltip
            label="Write timeout"
            tooltip="Timeout before canceling single write task"
          />
        }
        placeholder="seconds"
        suffix=" s."
        min={0.1}
        step={0.1}
        {...form.getInputProps('write_timeout')}
        key={form.key('write_timeout')}
      />

      <Paper withBorder p="sm">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Batching
          </Text>
          <Radio.Group
            name="batchingMode"
            label="Batching mode"
            description="Batch is formed by at least one condition"
            value={batchingMode}
          >
            <Group mt="xs">
              <Tooltip
                withArrow
                label="Use only size condition for batch formation"
                position="bottom"
                offset={12}
                openDelay={200}
              >
                <Box>
                  <Radio
                    value="size"
                    label="Size"
                    onClick={() => {
                      setBatchingMode('size');
                      form.setFieldValue('batch.delay', null);
                    }}
                  />
                </Box>
              </Tooltip>
              <Tooltip
                withArrow
                label="Use only delay condition for batch formation"
                position="bottom"
                offset={12}
                openDelay={200}
              >
                <Box>
                  <Radio
                    value="delay"
                    label="Delay"
                    onClick={() => {
                      setBatchingMode('delay');
                      form.setFieldValue('batch.size', null);
                    }}
                  />
                </Box>
              </Tooltip>
              <Tooltip
                withArrow
                label="Use both size and delay conditions for batch formation. Batch is formed by the first true condition."
                position="bottom"
                offset={12}
                openDelay={200}
                maw={300}
                multiline
              >
                <Box>
                  <Radio
                    value="combined"
                    label="Combined"
                    onClick={() => {
                      setBatchingMode('combined');
                    }}
                  />
                </Box>
              </Tooltip>
            </Group>
          </Radio.Group>
          <Group grow align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Batch size"
                  tooltip="Maximum number of timestamps for single batch"
                />
              }
              placeholder="size"
              min={1}
              allowDecimal={false}
              disabled={batchingMode === 'delay'}
              {...form.getInputProps('batch.size')}
              key={form.key('batch.size')}
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Batch delay"
                  tooltip="Maximum time for single batch to accumulate incoming timestamps"
                />
              }
              placeholder="seconds"
              suffix=" s."
              min={0.1}
              step={0.1}
              disabled={batchingMode === 'size'}
              {...form.getInputProps('batch.delay')}
              key={form.key('batch.delay')}
            />
          </Group>
          <Alert
            variant="default"
            icon={<Box c="blue" component={IconInfoCircle}></Box>}
            title="Batch lifecycle"
          >
            Formed batch preserve its size throughout the entire workflow of
            plugins. At event plugin stage, batch is expanded from timestamps to
            events. So, for large events, smaller batch sizes are preferred.
          </Alert>
        </Stack>
      </Paper>

      <Paper withBorder p="sm">
        <Stack gap="xs">
          <Text size="sm" fw="bold">
            Queue
          </Text>
          <Group grow align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Maximum timestamp batches"
                  tooltip="Maximum number of batches in timestamps queue (between all input and event plugins)"
                />
              }
              placeholder="size"
              min={1}
              allowDecimal={false}
              {...form.getInputProps('queue.max_timestamp_batches')}
              key={form.key('queue.max_timestamp_batches')}
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Maximum event batches"
                  tooltip="Maximum number of batches in events queue (between event and output plugins)"
                />
              }
              placeholder="size"
              min={1}
              allowDecimal={false}
              {...form.getInputProps('queue.max_event_batches')}
              key={form.key('queue.max_event_batches')}
            />
          </Group>
          <QueueSizeApproximation
            batchSize={batchSize}
            queueParams={queueParams}
          />
        </Stack>
      </Paper>
    </Stack>
  );
};
