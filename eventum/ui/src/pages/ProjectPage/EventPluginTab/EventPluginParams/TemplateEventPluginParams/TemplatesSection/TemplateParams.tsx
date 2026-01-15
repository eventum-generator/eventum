import {
  Button,
  NumberInput,
  Select,
  Stack,
  Switch,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { zod4Resolver } from 'mantine-form-zod-resolver';
import { FC } from 'react';
import YAML from 'yaml';
import { z } from 'zod';

import {
  TemplateConfig,
  TemplateConfigForChanceMode,
  TemplateConfigForChanceModeSchema,
  TemplateConfigForFSMMode,
  TemplateConfigForFSMModeSchema,
  TemplateConfigForGeneralModesSchema,
  TemplatePickingMode,
} from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { LabelWithTooltip } from '@/components/ui/LabelWithTooltip';
import { ProjectFileSelect } from '@/pages/ProjectPage/components/ProjectFileSelect';

interface TemplateParamsProps {
  pickingMode: TemplatePickingMode;
  value: TemplateConfig;
  onChange: (value: TemplateConfig) => void;
  onDelete: (templatePath: string | undefined) => void;
  existingTemplates: string[];
}

const modeToSchema = {
  all: TemplateConfigForGeneralModesSchema,
  any: TemplateConfigForGeneralModesSchema,
  chain: TemplateConfigForGeneralModesSchema,
  chance: TemplateConfigForChanceModeSchema,
  fsm: TemplateConfigForFSMModeSchema,
  spin: TemplateConfigForGeneralModesSchema,
} as const satisfies Record<TemplatePickingMode, z.ZodType>;

export const TemplateParams: FC<TemplateParamsProps> = ({
  pickingMode,
  value,
  onChange,
  onDelete,
  existingTemplates,
}) => {
  const form = useForm<TemplateConfig>({
    initialValues: value,
    validate: zod4Resolver(modeToSchema[pickingMode]),
    onValuesChange: onChange,
    validateInputOnChange: true,
    cascadeUpdates: true,
  });

  return (
    <Stack gap="xs">
      <ProjectFileSelect
        label={
          <LabelWithTooltip label="Template" tooltip="Path to template file" />
        }
        {...form.getInputProps('template')}
        value={form.values.template ?? null}
        onChange={(value) => {
          form.setFieldValue('template', value ?? undefined!);
        }}
        searchable
        nothingFoundMessage="No files found"
        placeholder=".jinja"
        extensions={['.jinja']}
        clearable
        required
      />

      {pickingMode === TemplatePickingMode.Chance && (
        <NumberInput
          label={
            <LabelWithTooltip
              label="Chance"
              tooltip="Proportional value of probability for template to be picked for rendering"
            />
          }
          min={0}
          required
          {...form.getInputProps('chance')}
          value={(form.values as TemplateConfigForChanceMode).chance ?? ''}
          onChange={(value) => {
            form.setFieldValue(
              'chance',
              typeof value === 'number' ? value : undefined!
            );
          }}
        />
      )}

      {pickingMode === TemplatePickingMode.FSM && (
        <Stack gap="xs">
          <Switch
            label={
              <LabelWithTooltip
                label="Initial"
                tooltip="Set this template as initial state"
              />
            }
            {...form.getInputProps('initial', { type: 'checkbox' })}
            checked={(form.values as TemplateConfigForFSMMode).initial ?? false}
          />
          <Select
            label={
              <LabelWithTooltip
                label="To"
                tooltip="Name of template of next state after transition"
              />
            }
            data={existingTemplates}
            searchable
            nothingFoundMessage="No template found"
            placeholder="template name"
            clearable
            {...form.getInputProps('transition.to')}
            value={
              (form.values as TemplateConfigForFSMMode).transition?.to ?? null
            }
            onChange={(value) => {
              form.setFieldValue('transition', (prevValue) => {
                if (value === null) {
                  return;
                }

                if (prevValue) {
                  return {
                    when: prevValue.when ?? undefined,
                    to: value ?? undefined!,
                  };
                }

                return {
                  when: undefined,
                  to: value ?? undefined!,
                };
              });
            }}
          />
          <Stack gap="2px">
            <Textarea
              label="When"
              description="Condition for performing transition to next state in YAML format. See examples in documentation."
              placeholder="..."
              minRows={3}
              autosize
              disabled={
                (form.values as TemplateConfigForFSMMode).transition?.to ===
                undefined
              }
              defaultValue={YAML.stringify(
                (form.values as TemplateConfigForFSMMode).transition?.when
              )}
              onChange={(event) => {
                let parsedValue: unknown;

                if (!event.currentTarget.value) {
                  parsedValue = undefined;
                } else {
                  try {
                    parsedValue = YAML.parse(event.currentTarget.value);
                  } catch {
                    return;
                  }
                }

                form.setFieldValue('transition.when', parsedValue);
              }}
              error={form.errors['transition.when']}
            />
          </Stack>
        </Stack>
      )}

      <Button variant="default" onClick={() => onDelete(form.values.template)}>
        Remove
      </Button>
    </Stack>
  );
};
