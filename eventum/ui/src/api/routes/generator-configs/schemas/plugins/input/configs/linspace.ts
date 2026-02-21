import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { BaseInputPluginConfigSchema } from '../base-config';
import { VersatileDatetimeStrictSchema } from '../versatile-datetime';

export const LinspaceInputPluginConfigSchema =
  BaseInputPluginConfigSchema.extend({
    start: VersatileDatetimeStrictSchema,
    end: VersatileDatetimeStrictSchema,
    count: orPlaceholder(z.number().int().gte(1)),
    endpoint: orPlaceholder(z.boolean()).optional(),
  });
export type LinspaceInputPluginConfig = z.infer<
  typeof LinspaceInputPluginConfigSchema
>;
export const LinspaceInputPluginNamedConfigSchema = z.object({
  linspace: LinspaceInputPluginConfigSchema,
});
