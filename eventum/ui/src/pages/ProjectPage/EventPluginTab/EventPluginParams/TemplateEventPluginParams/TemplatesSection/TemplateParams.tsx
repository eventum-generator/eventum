import {
  Button,
  JsonInput,
  NumberInput,
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
  TemplateTransitionsSchema,
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
            checked={
              ((form.values as TemplateConfigForFSMMode).initial ?? false) ===
              true
            }
          />
          <Stack gap="2px">
            <Textarea
              label="Transitions"
              description="List of transitions in YAML format. See examples in documentation."
              placeholder="..."
              minRows={3}
              autosize
              defaultValue={YAML.stringify(
                (form.values as TemplateConfigForFSMMode).transitions
              )}
              onChange={(event) => {
                let parsedValue: unknown;

                try {
                  parsedValue = YAML.parse(event.currentTarget.value);

                  const validatedParsedValue =
                    TemplateTransitionsSchema.parse(parsedValue);
                  form.setFieldValue('transitions', validatedParsedValue);

                  for (const transition of validatedParsedValue) {
                    if (!existingTemplates.includes(transition.to)) {
                      form.setFieldError(
                        'transitions',
                        `Invalid target state, use one of: ${existingTemplates.join(', ')}`
                      );
                    }
                  }
                } catch {
                  form.setFieldError('transitions', 'Invalid input');
                  return;
                }
              }}
              error={form.errors.transitions}
            />
          </Stack>
        </Stack>
      )}

      <JsonInput
        label={
          <LabelWithTooltip
            label="Variables"
            tooltip="Per-template variables accessible via vars in the template"
          />
        }
        description="Each variable is an attribute of a single JSON object"
        placeholder="{ ... }"
        validationError="Invalid JSON"
        minRows={4}
        autosize
        defaultValue={JSON.stringify(form.values.vars, undefined, 2)}
        onChange={(value) => {
          if (!value) {
            form.setFieldValue('vars', undefined);
            return;
          }

          let parsed: unknown;
          try {
            parsed = JSON.parse(value);
          } catch {
            return;
          }

          if (typeof parsed === 'object') {
            form.setFieldValue('vars', parsed as Record<string, never>);
          }
        }}
        error={form.errors.vars}
      />

      <Button variant="default" onClick={() => onDelete(form.values.template)}>
        Remove
      </Button>
    </Stack>
  );
};
