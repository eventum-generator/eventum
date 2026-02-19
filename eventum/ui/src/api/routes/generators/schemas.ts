import z from 'zod';

import { GenerationParametersSchema } from '../instance/schemas';

export const GeneratorStatusSchema = z.object({
  is_initializing: z.boolean(),
  is_running: z.boolean(),
  is_ended_up: z.boolean(),
  is_ended_up_successfully: z.boolean(),
  is_stopping: z.boolean(),
});
export type GeneratorStatus = z.infer<typeof GeneratorStatusSchema>;

export const GeneratorsInfoSchema = z.array(
  z.object({
    id: z.string().min(1),
    path: z.string(),
    status: GeneratorStatusSchema,
    start_time: z.string().nullable(),
  })
);
export type GeneratorsInfo = z.infer<typeof GeneratorsInfoSchema>;

export const PluginStatsSchema = z.object({
  plugin_name: z.string().min(1),
  plugin_id: z.int().min(0),
});

export const InputPluginStatsSchema = PluginStatsSchema.extend({
  generated: z.int().min(0),
});
export type InputPluginStats = z.infer<typeof InputPluginStatsSchema>;

export const EventPluginStatsSchema = PluginStatsSchema.extend({
  produced: z.int().min(0),
  produce_failed: z.int().min(0),
});
export type EventPluginStats = z.infer<typeof EventPluginStatsSchema>;

export const OutputPluginStatsSchema = PluginStatsSchema.extend({
  written: z.int().min(0),
  write_failed: z.int().min(0),
  format_failed: z.int().min(0),
});
export type OutputPluginStats = z.infer<typeof OutputPluginStatsSchema>;

export const GeneratorStatsSchema = z.object({
  id: z.string(),
  start_time: z.string(),
  input: z.array(InputPluginStatsSchema),
  event: EventPluginStatsSchema,
  output: z.array(OutputPluginStatsSchema),
  total_generated: z.int(),
  total_written: z.int(),
  uptime: z.number(),
  input_eps: z.number(),
  output_eps: z.number(),
});
export type GeneratorStats = z.infer<typeof GeneratorStatsSchema>;

export const GeneratorParametersSchema = GenerationParametersSchema.extend({
  id: z.string().min(1),
  path: z.string(),
  live_mode: z.boolean().optional(),
  skip_past: z.boolean().optional(),
  params: z.record(z.string(), z.any()).optional(),
});
export type GeneratorParameters = z.infer<typeof GeneratorParametersSchema>;

export const BulkStartResponseSchema = z.object({
  running_generator_ids: z.array(z.string()),
  non_running_generator_ids: z.array(z.string()),
});
export type BulkStartResponse = z.infer<typeof BulkStartResponseSchema>;
