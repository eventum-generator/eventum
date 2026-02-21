import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { ENCODINGS } from '../../../encodings';
import { BaseEventPluginConfigSchema } from '../base-config';

export const ReplayEventPluginConfigSchema = BaseEventPluginConfigSchema.extend(
  {
    path: z.string().min(1),
    timestamp_pattern: z.string().min(1).nullable().optional(),
    timestamp_format: z.string().min(1).nullable().optional(),
    repeat: orPlaceholder(z.boolean()).optional(),
    chunk_size: orPlaceholder(z.number().int().gte(0)).optional(),
    encoding: orPlaceholder(z.enum(ENCODINGS)).optional(),
  }
);
export type ReplayEventPluginConfig = z.infer<
  typeof ReplayEventPluginConfigSchema
>;
export const ReplayEventPluginNamedConfigSchema = z.object({
  replay: ReplayEventPluginConfigSchema,
});
