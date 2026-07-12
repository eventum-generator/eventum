import { Checkbox, Group, JsonInput, Stack, Switch } from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import { FC } from 'react';

import { Section } from '../primitives';
import { GenerationParameters } from '@/api/routes/instance/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { GenerationParametersSection } from '@/pages/SettingsPage/GenerationParametersSection';

interface SettingsTabProps {
  form: UseFormReturnType<StartupGeneratorParameters>;
}

/**
 * Editable instance configuration: runtime toggles and substitution params,
 * plus the shared generation-parameters section. Changes propagate through
 * the parent form; saving is driven from the page header.
 */
export const SettingsTab: FC<SettingsTabProps> = ({ form }) => (
  <Stack gap="xl">
    <Section label="Runtime">
      <Stack gap="md">
        <Group gap="xl">
          <Switch
            label={
              <LabelWithTooltip
                label="Live mode"
                tooltip="Whether to use live mode and generate events at moments defined by timestamp values or sample mode to generate all events at a time"
              />
            }
            {...form.getInputProps('live_mode', { type: 'checkbox' })}
            key={form.key('live_mode')}
          />
          <Switch
            label={
              <LabelWithTooltip
                label="Skip past"
                tooltip="Whether to skip past timestamps when starting generation in live mode"
              />
            }
            {...form.getInputProps('skip_past', { type: 'checkbox' })}
            key={form.key('skip_past')}
          />
          <Checkbox
            label={
              <LabelWithTooltip
                label="Auto start"
                tooltip="Whether to automatically start the generator on application start up"
              />
            }
            {...form.getInputProps('autostart', { type: 'checkbox' })}
            key={form.key('autostart')}
          />
        </Group>

        <JsonInput
          label="Parameters"
          description="Parameters that can be used in generator configuration file"
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
      </Stack>
    </Section>

    <Section label="Generation">
      <GenerationParametersSection
        form={form as unknown as UseFormReturnType<GenerationParameters>}
      />
    </Section>
  </Stack>
);
