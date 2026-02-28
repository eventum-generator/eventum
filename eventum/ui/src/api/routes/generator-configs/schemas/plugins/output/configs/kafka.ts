import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { ENCODINGS } from '../../../encodings';
import { BaseOutputPluginConfigSchema } from '../base-config';

export const SECURITY_PROTOCOLS = [
  'PLAINTEXT',
  'SSL',
  'SASL_PLAINTEXT',
  'SASL_SSL',
] as const;

export const SASL_MECHANISMS = [
  'PLAIN',
  'SCRAM-SHA-256',
  'SCRAM-SHA-512',
] as const;

export const COMPRESSION_TYPES = [
  'gzip',
  'snappy',
  'lz4',
  'zstd',
] as const;

export const ACKS_VALUES = [0, 1, -1] as const;

export const KafkaOutputPluginConfigSchema =
  BaseOutputPluginConfigSchema.extend({
    // Connection
    bootstrap_servers: z.array(z.string().min(1)).min(1),
    client_id: z.string().min(1).nullable().optional(),
    metadata_max_age_ms: orPlaceholder(z.number().int().gte(0)).optional(),
    request_timeout_ms: orPlaceholder(z.number().int().gte(1)).optional(),
    connections_max_idle_ms: orPlaceholder(z.number().int().gte(0)).optional(),

    // Topic & Message
    topic: z.string().min(1),
    key: z.string().min(1).nullable().optional(),
    encoding: orPlaceholder(z.enum(ENCODINGS)).optional(),

    // Performance & Reliability
    acks: orPlaceholder(z.union([
      z.literal(0),
      z.literal(1),
      z.literal(-1),
    ])).optional(),
    compression_type: orPlaceholder(
      z.enum(COMPRESSION_TYPES),
    ).nullable().optional(),
    max_batch_size: orPlaceholder(z.number().int().gte(1)).optional(),
    max_request_size: orPlaceholder(z.number().int().gte(1)).optional(),
    linger_ms: orPlaceholder(z.number().int().gte(0)).optional(),
    retry_backoff_ms: orPlaceholder(z.number().int().gte(0)).optional(),
    enable_idempotence: orPlaceholder(z.boolean()).optional(),
    transactional_id: z.string().min(1).nullable().optional(),
    transaction_timeout_ms: orPlaceholder(z.number().int().gte(1)).optional(),

    // Security
    security_protocol: orPlaceholder(
      z.enum(SECURITY_PROTOCOLS),
    ).optional(),
    sasl_mechanism: orPlaceholder(
      z.enum(SASL_MECHANISMS),
    ).nullable().optional(),
    sasl_plain_username: z.string().min(1).nullable().optional(),
    sasl_plain_password: z.string().min(1).nullable().optional(),
    sasl_kerberos_service_name: z.string().min(1).optional(),
    sasl_kerberos_domain_name: z.string().min(1).nullable().optional(),

    // SSL/TLS
    ssl_cafile: z.string().min(1).nullable().optional(),
    ssl_certfile: z.string().min(1).nullable().optional(),
    ssl_keyfile: z.string().min(1).nullable().optional(),
  });
export type KafkaOutputPluginConfig = z.infer<
  typeof KafkaOutputPluginConfigSchema
>;
export const KafkaOutputPluginNamedConfigSchema = z.object({
  kafka: KafkaOutputPluginConfigSchema,
});
