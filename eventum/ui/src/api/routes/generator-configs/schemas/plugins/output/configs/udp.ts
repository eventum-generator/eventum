import z from 'zod';

import { ENCODINGS } from '../../../encodings';
import { orPlaceholder } from '../../../placeholder';
import { BaseOutputPluginConfigSchema } from '../base-config';

export const UdpOutputPluginConfigSchema = BaseOutputPluginConfigSchema.extend({
  host: z.string().min(1),
  port: orPlaceholder(z.number().int().gte(1).lte(65_535)),
  encoding: orPlaceholder(z.enum(ENCODINGS)).optional(),
  separator: z.string().optional(),
});
export type UdpOutputPluginConfig = z.infer<typeof UdpOutputPluginConfigSchema>;
export const UdpOutputPluginNamedConfigSchema = z.object({
  udp: UdpOutputPluginConfigSchema,
});
