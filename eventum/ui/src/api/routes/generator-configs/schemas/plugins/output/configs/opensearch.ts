import z from 'zod';

import { BaseOutputPluginConfigSchema } from '../base-config';

export const OpensearchOutputPluginConfigSchema =
  BaseOutputPluginConfigSchema.extend({
    hosts: z
      .array(z.url({ protocol: /^https?$/, hostname: z.regexes.hostname }))
      .min(1),
    username: z.string().min(1),
    password: z.string().min(1),
    index: z.string().min(1),
    connect_timeout: z.number().int().gte(1).optional(),
    request_timeout: z.number().int().gte(1).optional(),
    verify: z.boolean().optional(),
    ca_cert: z.string().min(1).nullable().optional(),
    client_cert: z.string().min(1).nullable().optional(),
    client_cert_key: z.string().min(1).nullable().optional(),
    proxy_url: z.httpUrl().nullable().optional(),
  });
export type OpensearchOutputPluginConfig = z.infer<
  typeof OpensearchOutputPluginConfigSchema
>;
export const OpensearchOutputPluginNamedConfigSchema = z.object({
  opensearch: OpensearchOutputPluginConfigSchema,
});
