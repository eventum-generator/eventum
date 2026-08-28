import {
  Box,
  Divider,
  Group,
  JsonInput,
  SegmentedControl,
  Stack,
  Switch,
  Text,
} from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import {
  IconActivityHeartbeat,
  IconDatabase,
  IconHistory,
  IconRocket,
} from '@tabler/icons-react';
import { FC, ReactNode, useState } from 'react';

import { Section } from '../primitives';
import { GenerationParameters } from '@/api/routes/instance/schemas';
import { StartupGeneratorParameters } from '@/api/routes/startup/schemas';
import { GenerationParametersSection } from '@/pages/SettingsPage/GenerationParametersSection';

interface SettingsTabProps {
  form: UseFormReturnType<StartupGeneratorParameters>;
}

/** Title over a muted description, shared by every runtime setting. */
const SettingHead: FC<{ title: string; description: ReactNode }> = ({
  title,
  description,
}) => (
  <Box style={{ minWidth: 0 }}>
    <Text size="sm" fw={600}>
      {title}
    </Text>
    <Text size="xs" c="dimmed">
      {description}
    </Text>
  </Box>
);

/** A boolean setting: icon + labelled description on the left, switch right. */
const ToggleSetting: FC<{
  icon: ReactNode;
  title: string;
  description: ReactNode;
  disabled?: boolean;
  children: ReactNode;
}> = ({ icon, title, description, disabled, children }) => (
  <Group
    justify="space-between"
    wrap="nowrap"
    gap="xl"
    style={{ opacity: disabled ? 0.55 : 1 }}
  >
    <Group gap="sm" wrap="nowrap" align="flex-start">
      <Box c="dimmed" style={{ display: 'flex', flexShrink: 0, marginTop: 2 }}>
        {icon}
      </Box>
      <SettingHead title={title} description={description} />
    </Group>
    <Box style={{ flexShrink: 0 }}>{children}</Box>
  </Group>
);

/**
 * Editable instance configuration: the instance-specific runtime settings -
 * each drawn to fit what it controls (emission mode as a choice, the past-skip
 * toggle gated on live mode, autostart, substitution parameters) - plus the
 * shared generation-parameters section. Changes propagate through the parent
 * form; saving is driven from the page header.
 */
export const SettingsTab: FC<SettingsTabProps> = ({ form }) => {
  const [liveMode, setLiveMode] = useState(form.getValues().live_mode ?? false);
  form.watch('live_mode', ({ value }) => setLiveMode(value ?? false));

  return (
    <Stack gap="xl">
      <Section label="Runtime">
        <Stack gap="lg">
          <Box>
            <SettingHead
              title="Emission mode"
              description="How generated events are emitted over time."
            />
            <SegmentedControl
              mt="sm"
              fullWidth
              value={liveMode ? 'live' : 'sample'}
              onChange={(value) =>
                form.setFieldValue('live_mode', value === 'live')
              }
              data={[
                {
                  value: 'sample',
                  label: (
                    <Group gap={8} justify="center" wrap="nowrap">
                      <IconDatabase size={16} />
                      <span>Sample</span>
                    </Group>
                  ),
                },
                {
                  value: 'live',
                  label: (
                    <Group gap={8} justify="center" wrap="nowrap">
                      <IconActivityHeartbeat size={16} />
                      <span>Live</span>
                    </Group>
                  ),
                },
              ]}
            />
            <Text size="xs" c="dimmed" mt={8}>
              {liveMode
                ? 'Events are emitted at their timestamp moments, in real time.'
                : 'All events are emitted at once, as fast as the pipeline allows.'}
            </Text>
          </Box>

          <Divider />

          <ToggleSetting
            icon={<IconHistory size={16} />}
            title="Skip past timestamps"
            description={
              liveMode
                ? 'On start, skip timestamps that already lie in the past.'
                : 'Only applies in live mode.'
            }
            disabled={!liveMode}
          >
            <Switch
              // The title of the setting sits across the row from the
              // switch rather than beside it, so the switch names
              // itself - otherwise it is a control with no name.
              aria-label="Skip past timestamps"
              {...form.getInputProps('skip_past', { type: 'checkbox' })}
              key={form.key('skip_past')}
              disabled={!liveMode}
            />
          </ToggleSetting>

          <Divider />

          <ToggleSetting
            icon={<IconRocket size={16} />}
            title="Autostart"
            description="Start this instance automatically when the application launches."
          >
            <Switch
              aria-label="Autostart"
              {...form.getInputProps('autostart', { type: 'checkbox' })}
              key={form.key('autostart')}
            />
          </ToggleSetting>

          <Divider />

          <Box>
            <SettingHead
              title="Parameters"
              description={
                'Values substituted into the generator configuration as ${params.*} placeholders.'
              }
            />
            <JsonInput
              mt="sm"
              placeholder="{ ... }"
              validationError="Invalid JSON"
              minRows={4}
              autosize
              // No parameters is an empty object rather than an empty
              // string: the field holds an object, and a string in it
              // parses but is never a value the form can take.
              defaultValue={JSON.stringify(
                form.getValues().params ?? {},
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
          liveMode={liveMode}
        />
      </Section>
    </Stack>
  );
};
