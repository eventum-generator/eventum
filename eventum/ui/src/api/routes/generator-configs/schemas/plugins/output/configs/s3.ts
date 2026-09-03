import z from 'zod';

import { orPlaceholder } from '../../../placeholder';
import { BaseOutputPluginConfigSchema } from '../base-config';

export const enum Encoding {
  JSONLines = 'jsonl',
  Parquet = 'parquet',
}

export const ADDRESSING_STYLES = ['auto', 'path', 'virtual'] as const;

export const JSON_LINES_COMPRESSIONS = ['none', 'gzip', 'zstd'] as const;

export const PARQUET_COMPRESSIONS = [
  'none',
  'snappy',
  'gzip',
  'zstd',
  'brotli',
  'lz4',
] as const;

export const MAX_GZIP_COMPRESSION_LEVEL = 9;

export const MAX_ZSTD_COMPRESSION_LEVEL = 22;

const JSONLinesEncoderConfigSchema = z.object({
  encoding: z.literal(Encoding.JSONLines),
  separator: z.string().min(1).optional(),
  compression: orPlaceholder(z.enum(JSON_LINES_COMPRESSIONS)).optional(),
  compression_level: orPlaceholder(
    z.number().int().gte(1).lte(MAX_ZSTD_COMPRESSION_LEVEL)
  )
    .nullable()
    .optional(),
});

const ParquetEncoderConfigSchema = z.object({
  encoding: z.literal(Encoding.Parquet),
  compression: orPlaceholder(z.enum(PARQUET_COMPRESSIONS)).optional(),
  row_group_size: orPlaceholder(z.number().int().gte(1)).optional(),
  schema_path: z.string().min(1).nullable().optional(),
});

export const EncoderConfigSchema = z.discriminatedUnion('encoding', [
  JSONLinesEncoderConfigSchema,
  ParquetEncoderConfigSchema,
]);
export type EncoderConfig = z.infer<typeof EncoderConfigSchema>;

export const S3OutputPluginConfigSchema = BaseOutputPluginConfigSchema.extend({
  bucket: z.string().min(1),
  key_template: z.string().min(1).optional(),
  endpoint_url: orPlaceholder(z.httpUrl()).nullable().optional(),
  region: z.string().min(1).optional(),
  addressing_style: orPlaceholder(z.enum(ADDRESSING_STYLES)).optional(),
  access_key_id: z.string().min(1).nullable().optional(),
  secret_access_key: z.string().min(1).nullable().optional(),
  session_token: z.string().min(1).nullable().optional(),
  encoder: EncoderConfigSchema.optional(),
  content_type: z.string().min(1).nullable().optional(),
  connect_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
  request_timeout: orPlaceholder(z.number().int().gte(1)).optional(),
  max_retries: orPlaceholder(z.number().int().gte(0)).optional(),
  verify: orPlaceholder(z.boolean()).optional(),
  ca_cert: z.string().min(1).nullable().optional(),
  proxy_url: orPlaceholder(z.httpUrl()).nullable().optional(),
});
export type S3OutputPluginConfig = z.infer<typeof S3OutputPluginConfigSchema>;
export const S3OutputPluginNamedConfigSchema = z.object({
  s3: S3OutputPluginConfigSchema,
});
