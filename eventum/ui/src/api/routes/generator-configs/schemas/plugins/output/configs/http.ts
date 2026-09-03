import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { HTTPAuthConfigSchema } from '../auth';
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

export const HTTPOutputPluginConfigShape = BaseOutputPluginConfigSchema.extend({
  url: orPlaceholder(z.httpUrl()),
  method: orPlaceholder(z.enum(HTTP_METHODS)).optional(),
  success_code: orPlaceholder(z.number().int().gte(100).lt(600)).optional(),
  headers: z.record(z.string().min(1), z.string()).optional(),
  auth: HTTPAuthConfigSchema.nullable().optional(),
  connect_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
  request_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
  verify: orPlaceholder(z.boolean()).optional(),
  ca_cert: z.string().min(1).nullable().optional(),
  client_cert: z.string().min(1).nullable().optional(),
  client_cert_key: z.string().min(1).nullable().optional(),
  proxy_url: orPlaceholder(z.httpUrl()).nullable().optional(),
  concurrency: orPlaceholder(z.number().int().gte(1)).optional(),
});

/** The plugin sets the header itself, so the two cannot be combined. */
export const HTTPOutputPluginConfigSchema =
  HTTPOutputPluginConfigShape.superRefine((config, ctx) => {
    if (config.auth === null || config.auth === undefined) {
      return;
    }

    const written = Object.keys(config.headers ?? {}).find(
      (header) => header.toLowerCase() === 'authorization'
    );

    if (written !== undefined) {
      ctx.addIssue({
        code: 'custom',
        path: ['headers'],
        message:
          'The Authorization header cannot be set together with auth; ' +
          'keep one of them',
      });
    }
  });
export type HTTPOutputPluginConfig = z.infer<
  typeof HTTPOutputPluginConfigSchema
>;
export const HTTPOutputPluginNamedConfigSchema = z.object({
  http: HTTPOutputPluginConfigSchema,
});
