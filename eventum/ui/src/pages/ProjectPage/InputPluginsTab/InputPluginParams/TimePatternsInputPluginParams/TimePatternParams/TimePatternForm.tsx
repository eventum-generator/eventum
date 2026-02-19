import {
  Center,
  Divider,
  Group,
  NumberInput,
  RangeSlider,
  SegmentedControl,
  Select,
  Slider,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import { UseFormReturnType } from '@mantine/form';
import {
  IconArrowDown,
  IconArrowUp,
  IconArrowsMoveVertical,
  IconSquare,
  IconTilde,
  IconTriangle,
} from '@tabler/icons-react';
import { FC, ReactNode } from 'react';

import {
  Distribution,
  RandomizerDirection,
  TIME_UNITS,
  TimePatternConfig,
  TriangularDistributionParameters,
  UniformDistributionParameters,
} from '@/api/routes/generator-configs/schemas/plugins/input/configs/time_patterns';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { VersatileDatetimeInput } from '@/pages/ProjectPage/VersatileDatetimeInput';

interface TimePatternFormProps {
  form: UseFormReturnType<TimePatternConfig>;
}

export const TimePatternForm: FC<TimePatternFormProps> = ({ form }) => {
  return (
    <Stack gap="sm">
      <Stack gap="4px">
        <Text size="sm" fw="bold">
          General
        </Text>
        <Divider />
        <Textarea
          label="Label"
          description="Description of time pattern"
          placeholder="..."
          minRows={3}
          {...form.getInputProps('label', { type: 'input' })}
        />
      </Stack>

      <Stack gap="4px">
        <Text size="sm" fw="bold">
          Oscillator
        </Text>
        <Divider />
        <Stack gap="xs">
          <Group grow wrap="nowrap" align="start">
            <VersatileDatetimeInput
              label={
                <LabelWithTooltip
                  label="Start time"
                  tooltip="Start time of the distribution"
                />
              }
              {...form.getInputProps('oscillator.start', { type: 'input' })}
            />
            <VersatileDatetimeInput
              label={
                <LabelWithTooltip
                  label="End time"
                  tooltip="End time of the distribution"
                />
              }
              {...form.getInputProps('oscillator.end', { type: 'input' })}
            />
          </Group>
          <Group grow wrap="nowrap" align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Period"
                  tooltip="Duration of one period"
                />
              }
              placeholder="number"
              min={0.1}
              value={form.getValues().oscillator.period}
              onChange={(value) =>
                form.setFieldValue(
                  'oscillator.period',
                  typeof value === 'number' ? value : 0
                )
              }
            />
            <Select
              label={
                <LabelWithTooltip
                  label="Period unit"
                  tooltip="Time unit of the period"
                />
              }
              data={TIME_UNITS}
              placeholder="unit"
              clearable
              {...form.getInputProps('oscillator.unit', { type: 'input' })}
            />
          </Group>
        </Stack>
      </Stack>

      <Stack gap="4px">
        <Text size="sm" fw="bold">
          Multiplier
        </Text>
        <Divider />
        <NumberInput
          label={
            <LabelWithTooltip
              label="Ratio"
              tooltip="Multiplication ratio (i.e. number of timestamps per each oscillation/period)"
            />
          }
          placeholder="ratio"
          min={1}
          allowDecimal={false}
          {...form.getInputProps('multiplier.ratio', { type: 'input' })}
        />
      </Stack>

      <Stack gap="4px">
        <Text size="sm" fw="bold">
          Randomizer
        </Text>
        <Divider />
        <Stack gap="xs">
          <Group grow wrap="nowrap" align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Deviation"
                  tooltip="Deviation ratio (i.e. percent of timestamps amount deviation per period)"
                />
              }
              placeholder="ratio"
              min={0}
              max={1}
              step={0.05}
              {...form.getInputProps('randomizer.deviation', {
                type: 'input',
              })}
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Sampling"
                  tooltip="Size of sample with random deviation ratios"
                />
              }
              placeholder="number"
              min={16}
              allowDecimal={false}
              {...form.getInputProps('randomizer.sampling', {
                type: 'input',
              })}
            />
          </Group>
          <SegmentedControl
            title="Deviation direction"
            data={
              [
                {
                  label: (
                    <Center>
                      <Group gap="2px">
                        <IconArrowDown size={14} />
                        <span>Decrease</span>
                      </Group>
                    </Center>
                  ),
                  value: 'decrease',
                },
                {
                  label: (
                    <Center>
                      <Group gap="2px">
                        <IconArrowUp size={14} />
                        <span>Increase</span>
                      </Group>
                    </Center>
                  ),
                  value: 'increase',
                },
                {
                  label: (
                    <Center>
                      <Group gap="2px">
                        <IconArrowsMoveVertical size={14} />
                        <span>Mixed</span>
                      </Group>
                    </Center>
                  ),
                  value: 'mixed',
                },
              ] satisfies { label: ReactNode; value: RandomizerDirection }[]
            }
            {...form.getInputProps('randomizer.direction', {
              type: 'input',
            })}
          />
        </Stack>
      </Stack>

      <Stack gap="4px">
        <Text size="sm" fw="bold">
          Spreader
        </Text>
        <Divider />
        <SegmentedControl
          title="Distribution function"
          data={[
            {
              label: (
                <Center>
                  <Group gap="4px">
                    <IconTilde size={14} />
                    <span>Beta</span>
                  </Group>
                </Center>
              ),
              value: Distribution.BETA,
            },
            {
              label: (
                <Center>
                  <Group gap="4px">
                    <IconTriangle size={14} />
                    <span>Triangular</span>
                  </Group>
                </Center>
              ),
              value: Distribution.TRIANGULAR,
            },
            {
              label: (
                <Center>
                  <Group gap="4px">
                    <IconSquare size={14} />
                    <span>Uniform</span>
                  </Group>
                </Center>
              ),
              value: Distribution.UNIFORM,
            },
          ]}
          {...form.getInputProps('spreader.distribution', {
            type: 'input',
          })}
          onChange={(value) => {
            form.setFieldValue('spreader.distribution', value as Distribution);

            if ((value as Distribution) === Distribution.BETA) {
              form.setFieldValue('spreader.parameters.a', 15);
              form.setFieldValue('spreader.parameters.b', 15);
            } else if ((value as Distribution) === Distribution.TRIANGULAR) {
              form.setFieldValue('spreader.parameters.left', 0);
              form.setFieldValue('spreader.parameters.mode', 0.5);
              form.setFieldValue('spreader.parameters.right', 1);
            } else if ((value as Distribution) === Distribution.UNIFORM) {
              form.setFieldValue('spreader.parameters.low', 0);
              form.setFieldValue('spreader.parameters.high', 1);
            }
          }}
          mt="4px"
        />
        {form.getValues().spreader.distribution === Distribution.BETA && (
          <Group grow wrap="nowrap" align="start">
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Alpha"
                  tooltip="Parameter 'α' of the beta distribution"
                />
              }
              min={0}
              placeholder="number"
              {...form.getInputProps('spreader.parameters.a', {
                type: 'input',
              })}
            />
            <NumberInput
              label={
                <LabelWithTooltip
                  label="Beta"
                  tooltip="Parameter 'β' of the beta distribution"
                />
              }
              min={0}
              placeholder="number"
              {...form.getInputProps('spreader.parameters.b', {
                type: 'input',
              })}
            />
          </Group>
        )}

        {form.getValues().spreader.distribution === Distribution.TRIANGULAR && (
          <Stack gap="xs">
            <Stack gap="4px">
              <Text size="sm">Mode</Text>
              <Slider
                domain={[-0.1, 1.1]}
                min={
                  (
                    form.getValues().spreader
                      .parameters as TriangularDistributionParameters
                  )?.left ?? 0
                }
                max={
                  (
                    form.getValues().spreader
                      .parameters as TriangularDistributionParameters
                  )?.right ?? 1
                }
                step={0.01}
                label={(value) =>
                  (form.getValues().oscillator.period * value)
                    .toFixed(2)
                    .toString()
                }
                defaultValue={
                  (
                    form.getValues().spreader
                      .parameters as TriangularDistributionParameters
                  )?.mode ?? 0.5
                }
                onChangeEnd={(mode) => {
                  form.setFieldValue('spreader.parameters.mode', mode);
                }}
                key={form.key('spreader.parameters.mode')}
                styles={{ bar: { visibility: 'hidden' } }}
              />
            </Stack>
            <Stack gap="4px">
              <Text size="sm">Left and right</Text>
              <RangeSlider
                domain={[-0.1, 1.1]}
                min={0}
                max={1}
                step={0.01}
                minRange={0.01}
                marks={[
                  { value: 0, label: '0' },
                  {
                    value: 0.25,
                    label: (form.getValues().oscillator.period * 0.25)
                      .toFixed(2)
                      .toString(),
                  },
                  {
                    value: 0.5,
                    label: (form.getValues().oscillator.period * 0.5)
                      .toFixed(2)
                      .toString(),
                  },
                  {
                    value: 0.75,
                    label: (form.getValues().oscillator.period * 0.75)
                      .toFixed(2)
                      .toString(),
                  },
                  {
                    value: 1,
                    label: form
                      .getValues()
                      .oscillator.period.toFixed(2)
                      .toString(),
                  },
                ]}
                label={(value) =>
                  (form.getValues().oscillator.period * value)
                    .toFixed(2)
                    .toString()
                }
                defaultValue={[
                  (
                    form.getValues().spreader
                      .parameters as TriangularDistributionParameters
                  )?.left ?? 0,
                  (
                    form.getValues().spreader
                      .parameters as TriangularDistributionParameters
                  )?.right ?? 1,
                ]}
                onChangeEnd={([left, right]) => {
                  form.setFieldValue('spreader.parameters.left', left);
                  form.setFieldValue('spreader.parameters.right', right);

                  const mode = (
                    form.getValues().spreader
                      .parameters as TriangularDistributionParameters
                  )?.mode;

                  if (mode != undefined) {
                    if (mode < left) {
                      form.setFieldValue('spreader.parameters.mode', left);
                    } else if (mode > right) {
                      form.setFieldValue('spreader.parameters.mode', right);
                    }
                  }
                }}
              />
            </Stack>
          </Stack>
        )}

        {form.getValues().spreader.distribution === Distribution.UNIFORM && (
          <Stack gap="4px">
            <Text size="sm">Range</Text>
            <RangeSlider
              domain={[-0.1, 1.1]}
              min={0}
              max={1}
              step={0.01}
              minRange={0.01}
              marks={[
                { value: 0, label: '0' },
                {
                  value: 0.25,
                  label: (form.getValues().oscillator.period * 0.25)
                    .toFixed(2)
                    .toString(),
                },
                {
                  value: 0.5,
                  label: (form.getValues().oscillator.period * 0.5)
                    .toFixed(2)
                    .toString(),
                },
                {
                  value: 0.75,
                  label: (form.getValues().oscillator.period * 0.75)
                    .toFixed(2)
                    .toString(),
                },
                {
                  value: 1,
                  label: form
                    .getValues()
                    .oscillator.period.toFixed(2)
                    .toString(),
                },
              ]}
              label={(value) =>
                (form.getValues().oscillator.period * value)
                  .toFixed(2)
                  .toString()
              }
              defaultValue={[
                (
                  form.getValues().spreader
                    .parameters as UniformDistributionParameters
                )?.low ?? 0,
                (
                  form.getValues().spreader
                    .parameters as UniformDistributionParameters
                )?.high ?? 1,
              ]}
              onChangeEnd={([low, high]) => {
                form.setFieldValue('spreader.parameters.low', low);
                form.setFieldValue('spreader.parameters.high', high);
              }}
            />
          </Stack>
        )}
      </Stack>
    </Stack>
  );
};
