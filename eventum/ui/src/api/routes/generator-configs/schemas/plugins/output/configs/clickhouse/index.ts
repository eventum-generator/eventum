import z from 'zod';

import { orPlaceholder } from '../../../../placeholder';
import { BaseOutputPluginConfigSchema } from '../../base-config';
import { CLICKHOUSE_INPUT_FORMAT } from './clickhouse-input-formats';

export const PROTOCOLS = ['http', 'https'] as const;
export const TLS_MODES = ['proxy', 'strict', 'mutual'] as const;

export const ClickhouseOutputPluginConfigSchema =
  BaseOutputPluginConfigSchema.extend({
    host: z.string().min(1),
    port: orPlaceholder(z.number().int().gte(1).lte(65_535)).optional(),
    protocol: orPlaceholder(z.enum(PROTOCOLS)).optional(),
    database: z.string().min(1).optional(),
    table: z.string().min(1),
    username: z.string().min(1).optional(),
    password: z.string().optional(),
    dsn: z.string().min(1).nullable().optional(),
    connect_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
    request_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
    client_name: z.string().min(1).nullable().optional(),
    verify: orPlaceholder(z.boolean()).optional(),
    ca_cert: z.string().min(1).nullable().optional(),
    client_cert: z.string().min(1).nullable().optional(),
    client_cert_key: z.string().min(1).nullable().optional(),
    server_host_name: z.string().min(1).nullable().optional(),
    tls_mode: orPlaceholder(z.enum(TLS_MODES)).nullable().optional(),
    proxy_url: z.string().min(1).nullable().optional(),
    input_format: orPlaceholder(z.enum(CLICKHOUSE_INPUT_FORMAT)).optional(),
    header: z.string().optional(),
    footer: z.string().optional(),
    separator: z.string().optional(),
  });
export type ClickhouseOutputPluginConfig = z.infer<
  typeof ClickhouseOutputPluginConfigSchema
>;
export const ClickhouseOutputPluginNamedConfigSchema = z.object({
  clickhouse: ClickhouseOutputPluginConfigSchema,
});
