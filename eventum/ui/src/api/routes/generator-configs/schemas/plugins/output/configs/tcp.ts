import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { ENCODINGS } from '../../../encodings';
import { BaseOutputPluginConfigSchema } from '../base-config';

export const TcpOutputPluginConfigSchema =
  BaseOutputPluginConfigSchema.extend({
    host: z.string().min(1),
    port: orPlaceholder(z.number().int().gte(1).lte(65_535)),
    encoding: orPlaceholder(z.enum(ENCODINGS)).optional(),
    separator: z.string().optional(),
    connect_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
    ssl: orPlaceholder(z.boolean()).optional(),
    verify: orPlaceholder(z.boolean()).optional(),
    ca_cert: z.string().min(1).nullable().optional(),
    client_cert: z.string().min(1).nullable().optional(),
    client_cert_key: z.string().min(1).nullable().optional(),
  });
export type TcpOutputPluginConfig = z.infer<
  typeof TcpOutputPluginConfigSchema
>;
export const TcpOutputPluginNamedConfigSchema = z.object({
  tcp: TcpOutputPluginConfigSchema,
});
