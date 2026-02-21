import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { ENCODINGS } from '../../../encodings';
import { BaseOutputPluginConfigSchema } from '../base-config';

export const StdoutOutputPluginConfigSchema =
  BaseOutputPluginConfigSchema.extend({
    flush_interval: orPlaceholder(z.number().gte(0)).optional(),
    stream: orPlaceholder(z.enum(['stdout', 'stderr'])).optional(),
    encoding: orPlaceholder(z.enum(ENCODINGS)).optional(),
    separator: z.string().optional(),
  });
export type StdoutOutputPluginConfig = z.infer<
  typeof StdoutOutputPluginConfigSchema
>;
export const StdoutOutputPluginNamedConfigSchema = z.object({
  stdout: StdoutOutputPluginConfigSchema,
});
