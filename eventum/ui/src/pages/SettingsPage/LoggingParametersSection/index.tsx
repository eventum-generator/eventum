import { Group, NumberInput, Select, Stack } from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { FC } from 'react';

import {
  LOG_FORMATS,
  LOG_LEVELS,
  LogParameters,
} from '@/api/routes/instance/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';

interface LoggingParametersSectionProps {
  form: UseFormReturnType<LogParameters>;
}

export const LoggingParametersSection: FC<LoggingParametersSectionProps> = ({
  form,
}) => {
  return (
    <Stack gap="xs">
      <Select
        label={
          <LabelWithTooltip
            label="Logging level"
            tooltip="Minimal severity of messages to log"
          />
        }
        data={LOG_LEVELS}
        placeholder="level"
        {...form.getInputProps('level')}
        key={form.key('level')}
      />
      <Select
        label={
          <LabelWithTooltip label="Logs format" tooltip="Logging format" />
        }
        data={LOG_FORMATS}
        placeholder="format"
        {...form.getInputProps('format')}
        key={form.key('format')}
      />

      <Group grow align="start">
        <NumberInput
          label={
            <LabelWithTooltip
              label="Maximum bytes"
              tooltip="Maximum bytes for log file before rotation"
            />
          }
          min={1024}
          allowDecimal={false}
          placeholder="bytes"
          {...form.getInputProps('max_bytes')}
          key={form.key('max_bytes')}
        />
        <NumberInput
          label={
            <LabelWithTooltip
              label="Rotated files count"
              tooltip="Number of rotated log files to keep"
            />
          }
          min={1}
          allowDecimal={false}
          placeholder="number"
          {...form.getInputProps('backups')}
          key={form.key('backups')}
        />
      </Group>
    </Stack>
  );
};
