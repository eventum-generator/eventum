import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { BaseInputPluginConfigSchema } from '../base-config';
import { VersatileDatetimeSchema } from '../versatile-datetime';

export const CronInputPluginConfigSchema = BaseInputPluginConfigSchema.extend({
  start: VersatileDatetimeSchema.optional(),
  end: VersatileDatetimeSchema.optional(),
  expression: z.string(),
  count: orPlaceholder(z.number().int().gte(1)),
});
export type CronInputPluginConfig = z.infer<typeof CronInputPluginConfigSchema>;
export const CronInputPluginNamedConfigSchema = z.object({
  cron: CronInputPluginConfigSchema,
});
