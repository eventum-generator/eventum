import {
  Box,
  Divider,
  Group,
  JsonInput,
  Stack,
  Switch,
  Text,
} from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { FC, ReactNode } from 'react';

import { Section } from '../primitives';
import { GenerationParameters } from '@/api/routes/instance/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { GenerationParametersSection } from '@/pages/SettingsPage/GenerationParametersSection';

interface SettingsTabProps {
  form: UseFormReturnType<StartupGeneratorParameters>;
}

/** A labelled setting row: name + description on the left, control on the right. */
const SettingRow: FC<{
  label: string;
  description: string;
  control: ReactNode;
}> = ({ label, description, control }) => (
  <Group justify="space-between" wrap="nowrap" align="center" gap="xl">
    <Box style={{ minWidth: 0 }}>
      <Text size="sm" fw={500}>
        {label}
      </Text>
      <Text size="xs" c="dimmed">
        {description}
      </Text>
    </Box>
    <Box style={{ flexShrink: 0 }}>{control}</Box>
  </Group>
);

/**
 * Editable instance configuration: the instance-specific runtime settings
 * (presented as a labelled list to guide first-time setup) plus the shared
 * generation-parameters section. Changes propagate through the parent form;
 * saving is driven from the page header.
 */
export const SettingsTab: FC<SettingsTabProps> = ({ form }) => (
  <Stack gap="xl">
    <Section label="Runtime">
      <Stack gap="md">
        <SettingRow
          label="Live mode"
          description="Emit events at their timestamp moments (live) instead of all at once (sample)."
          control={
            <Switch
              {...form.getInputProps('live_mode', { type: 'checkbox' })}
              key={form.key('live_mode')}
            />
          }
        />
        <Divider />
        <SettingRow
          label="Skip past"
          description="When starting in live mode, skip timestamps that are already in the past."
          control={
            <Switch
              {...form.getInputProps('skip_past', { type: 'checkbox' })}
              key={form.key('skip_past')}
            />
          }
        />
        <Divider />
        <SettingRow
          label="Auto start"
          description="Start this instance automatically when the application starts."
          control={
            <Switch
              {...form.getInputProps('autostart', { type: 'checkbox' })}
              key={form.key('autostart')}
            />
          }
        />
        <Divider />
        <Box>
          <Text size="sm" fw={500}>
            Parameters
          </Text>
          <Text size="xs" c="dimmed" mb={8}>
            {
              'Values substituted into the generator configuration as ${params.*} placeholders.'
            }
          </Text>
          <JsonInput
            placeholder="{ ... }"
            validationError="Invalid JSON"
            minRows={4}
            autosize
            defaultValue={JSON.stringify(
              form.getValues().params ?? '',
              undefined,
              2
            )}
            onChange={(value) => {
              if (value === '') {
                form.setFieldValue('params', undefined);
              }

              let parsedValue: unknown;
              try {
                parsedValue = JSON.parse(value);
              } catch {
                return;
              }

              if (typeof parsedValue !== 'object') {
                return;
              }

              form.setFieldValue(
                'params',
                parsedValue as Record<string, unknown>
              );
            }}
            error={form.errors.params}
          />
        </Box>
      </Stack>
    </Section>

    <Section label="Generation">
      <GenerationParametersSection
        form={form as unknown as UseFormReturnType<GenerationParameters>}
      />
    </Section>
  </Stack>
);
