import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { BaseInputPluginConfigSchema } from '../base-config';

export const StaticInputPluginConfigSchema = BaseInputPluginConfigSchema.extend(
  {
    count: orPlaceholder(z.number().int().gte(1)),
  }
);
export type StaticInputPluginConfig = z.infer<
  typeof StaticInputPluginConfigSchema
>;
export const StaticInputPluginNamedConfigSchema = z.object({
  static: StaticInputPluginConfigSchema,
});
