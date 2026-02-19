import z from 'zod';

import { BaseOutputPluginConfigSchema } from '../base-config';

export const HTTP_METHODS = [
  'GET',
  'HEAD',
  'OPTIONS',
  'POST',
  'PUT',
  'PATCH',
  'DELETE',
];

export const HTTPOutputPluginConfigSchema = BaseOutputPluginConfigSchema.extend(
  {
    url: z.httpUrl(),
    method: z.enum(HTTP_METHODS).optional(),
    success_code: z.number().int().gte(100).lt(600).optional(),
    headers: z.record(z.string().min(1), z.any()).optional(),
    username: z.string().min(1).nullable().optional(),
    password: z.string().min(1).nullable().optional(),
    connect_timeout: z.number().int().gte(1).optional(),
    request_timeout: z.number().int().gte(1).optional(),
    verify: z.boolean().optional(),
    ca_cert: z.string().min(1).nullable().optional(),
    client_cert: z.string().min(1).nullable().optional(),
    client_cert_key: z.string().min(1).nullable().optional(),
    proxy_url: z.httpUrl().nullable().optional(),
  }
);
export type HTTPOutputPluginConfig = z.infer<
  typeof HTTPOutputPluginConfigSchema
>;
export const HTTPOutputPluginNamedConfigSchema = z.object({
  http: HTTPOutputPluginConfigSchema,
});
