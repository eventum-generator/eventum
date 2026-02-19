import z from 'zod';

import { FormatterConfigSchema } from '../generator-configs/schemas/plugins/output/formatters';

export const AggregatedTimestampsSchema = z.object({
  span_edges: z.array(z.string()),
  span_counts: z.record(z.string(), z.array(z.int())),
  total: z.int(),
  first_timestamps: z.array(z.string()).nullable(),
  last_timestamps: z.array(z.string()).nullable(),
  timestamps: z.array(z.string()).nullable(),
});
export type AggregatedTimestamps = z.infer<typeof AggregatedTimestampsSchema>;

export const ProduceParamsSchema = z.object({
  timestamp: z.string(),
  tags: z.string().array(),
});
export type ProduceParams = z.infer<typeof ProduceParamsSchema>;
export const ProduceParamsBodySchema = ProduceParamsSchema.array();
export type ProduceParamsBody = z.infer<typeof ProduceParamsBodySchema>;

const ProduceEventErrorInfoSchema = z.object({
  index: z.int().gte(0),
  message: z.string(),
  context: z.record(z.string(), z.any()),
});
export const ProducedEventsInfoSchema = z.object({
  events: z.string().array(),
  errors: ProduceEventErrorInfoSchema.array(),
  exhausted: z.boolean(),
});
export type ProducedEventsInfo = z.infer<typeof ProducedEventsInfoSchema>;

export const TemplateEventPluginStateSchema = z.record(z.string(), z.any());
export type TemplateEventPluginState = z.infer<
  typeof TemplateEventPluginStateSchema
>;

export const VersatileDatetimeParametersBodySchema = z.object({
  value: z.string().nullable().optional(),
  timezone: z.string().min(1),
  relative_base: z.string().nullable().optional(),
  none_point: z
    .union([z.literal('now'), z.literal('min'), z.literal('max')])
    .optional(),
});
export type VersatileDatetimeParametersBody = z.infer<
  typeof VersatileDatetimeParametersBodySchema
>;

export const VersatileDatetimeResponseSchema = z.string();
export type VersatileDatetimeResponse = z.infer<
  typeof VersatileDatetimeResponseSchema
>;

export const FormatEventsBodySchema = z.object({
  formatter_config: FormatterConfigSchema,
  events: z.array(z.string()).min(1),
});
export type FormatEventsBody = z.infer<typeof FormatEventsBodySchema>;

const FormatErrorInfoSchema = z.object({
  message: z.string(),
  original_event: z.string().nullable(),
});

export const FormattingResultSchema = z.object({
  events: z.array(z.string()),
  formatted_count: z.int(),
  errors: z.array(FormatErrorInfoSchema),
});
export type FormattingResult = z.infer<typeof FormattingResultSchema>;
