import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { ENCODINGS } from '../../../encodings';
import { BaseOutputPluginConfigSchema } from '../base-config';

export const WRITE_MODES = ['append', 'overwrite'] as const;

export const FileOutputPluginConfigSchema = BaseOutputPluginConfigSchema.extend(
  {
    path: z.string().min(1),
    flush_interval: orPlaceholder(z.number().gte(0)).optional(),
    cleanup_interval: orPlaceholder(z.number().gte(1)).optional(),
    file_mode: orPlaceholder(z.number().int().gte(0).lte(7777)).optional(),
    write_mode: orPlaceholder(z.enum(WRITE_MODES)).optional(),
    encoding: orPlaceholder(z.enum(ENCODINGS)).optional(),
    separator: z.string().optional(),
  }
);
export type FileOutputPluginConfig = z.infer<
  typeof FileOutputPluginConfigSchema
>;
export const FileOutputPluginNamedConfigSchema = z.object({
  file: FileOutputPluginConfigSchema,
});
