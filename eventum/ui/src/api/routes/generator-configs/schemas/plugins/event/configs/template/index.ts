import z from 'zod';

import { orPlaceholder } from '../../../../placeholder';
import { BaseEventPluginConfigSchema } from '../../base-config';
import { ConditionSchema } from './template-fsm-conditions';

export const enum SampleType {
  Items = 'items',
  CSV = 'csv',
  JSON = 'json',
}

export const enum TemplatePickingMode {
  All = 'all',
  Any = 'any',
  Chance = 'chance',
  Spin = 'spin',
  FSM = 'fsm',
  Chain = 'chain',
}

const ItemsSampleConfigSchema = z.object({
  type: z.literal(SampleType.Items),
  source: z.array(z.any()).min(1),
});
export type ItemsSampleConfig = z.infer<typeof ItemsSampleConfigSchema>;

const CSVSampleConfigSchema = z.object({
  type: z.literal(SampleType.CSV),
  header: orPlaceholder(z.boolean()).optional(),
  delimiter: z.string().min(1).optional(),
  source: z.string().endsWith('.csv'),
});
export type CSVSampleConfig = z.infer<typeof CSVSampleConfigSchema>;

const JSONSampleConfigSchema = z.object({
  type: z.literal(SampleType.JSON),
  source: z.string().endsWith('.json'),
});
export type JSONSampleConfig = z.infer<typeof JSONSampleConfigSchema>;

export const SampleConfigSchema = z.discriminatedUnion('type', [
  ItemsSampleConfigSchema,
  CSVSampleConfigSchema,
  JSONSampleConfigSchema,
]);
export type SampleConfig = z.infer<typeof SampleConfigSchema>;

export const TemplateConfigForGeneralModesSchema = z.object({
  template: z.string().endsWith('.jinja'),
});
export type TemplateConfigForGeneralModes = z.infer<
  typeof TemplateConfigForGeneralModesSchema
>;

export const TemplateConfigForChanceModeSchema =
  TemplateConfigForGeneralModesSchema.extend({
    chance: orPlaceholder(z.number().gt(0)),
  });
export type TemplateConfigForChanceMode = z.infer<
  typeof TemplateConfigForChanceModeSchema
>;

const TemplateTransitionSchema = z.object({
  to: z.string().min(1),
  when: ConditionSchema,
});

export const TemplateTransitionsSchema = TemplateTransitionSchema.array();
export type TemplateTransitions = z.infer<typeof TemplateTransitionsSchema>;

export const TemplateConfigForFSMModeSchema =
  TemplateConfigForGeneralModesSchema.extend({
    transitions: TemplateTransitionsSchema.optional(),
    initial: orPlaceholder(z.boolean()).optional(),
  });
export type TemplateConfigForFSMMode = z.infer<
  typeof TemplateConfigForFSMModeSchema
>;

export const TemplateConfigSchema = z.union([
  TemplateConfigForGeneralModesSchema,
  TemplateConfigForChanceModeSchema,
  TemplateConfigForFSMModeSchema,
]);
export type TemplateConfig = z.infer<typeof TemplateConfigSchema>;

const TemplateEventPluginConfigCommonFieldsSchema =
  BaseEventPluginConfigSchema.extend({
    params: z.record(z.string(), z.any()).optional(),
    samples: z.record(z.string(), SampleConfigSchema).optional(),
  });

const TemplateEventPluginConfigForGeneralModesSchema =
  TemplateEventPluginConfigCommonFieldsSchema.extend({
    mode: z.union([
      z.literal(TemplatePickingMode.All),
      z.literal(TemplatePickingMode.Any),
      z.literal(TemplatePickingMode.Spin),
    ]),
    templates: z
      .array(z.record(z.string().min(1), TemplateConfigForGeneralModesSchema))
      .min(1),
  });

const TemplateEventPluginConfigForChanceModeSchema =
  TemplateEventPluginConfigCommonFieldsSchema.extend({
    mode: z.literal(TemplatePickingMode.Chance),
    templates: z
      .array(z.record(z.string().min(1), TemplateConfigForChanceModeSchema))
      .min(1),
  });

const TemplateEventPluginConfigForFSMModeSchema =
  TemplateEventPluginConfigCommonFieldsSchema.extend({
    mode: z.literal(TemplatePickingMode.FSM),
    templates: z
      .array(z.record(z.string().min(1), TemplateConfigForFSMModeSchema))
      .min(1),
  });

const TemplateEventPluginConfigForChainModeSchema =
  TemplateEventPluginConfigCommonFieldsSchema.extend({
    mode: z.literal(TemplatePickingMode.Chain),
    chain: z.array(z.string().min(1)).min(1),
    templates: z
      .array(z.record(z.string().min(1), TemplateConfigForGeneralModesSchema))
      .min(1),
  });
export type TemplateEventPluginConfigForChainMode = z.infer<
  typeof TemplateEventPluginConfigForChainModeSchema
>;

export const TemplateEventPluginConfigSchema = z.discriminatedUnion('mode', [
  TemplateEventPluginConfigForGeneralModesSchema,
  TemplateEventPluginConfigForChanceModeSchema,
  TemplateEventPluginConfigForFSMModeSchema,
  TemplateEventPluginConfigForChainModeSchema,
]);
export type TemplateEventPluginConfig = z.infer<
  typeof TemplateEventPluginConfigSchema
>;
export const TemplateEventPluginNamedConfigSchema = z.object({
  template: TemplateEventPluginConfigSchema,
});
