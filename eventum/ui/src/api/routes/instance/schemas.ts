import { z } from 'zod';

import { TIMEZONES } from '@/api/schemas/timezones';

export const InstanceInfoSchema = z.object({
  app_version: z.string(),
  python_version: z.string(),
  python_implementation: z.string(),
  python_compiler: z.string(),
  platform: z.string(),
  host_name: z.string(),
  host_ip_v4: z.string(),
  boot_timestamp: z.number(),
  cpu_count: z.number().nullable(),
  cpu_frequency_mhz: z.number(),
  cpu_percent: z.number(),
  memory_total_bytes: z.number().int(),
  memory_used_bytes: z.number().int(),
  memory_available_bytes: z.number().int(),
  network_sent_bytes: z.number().int(),
  network_received_bytes: z.number().int(),
  disk_written_bytes: z.number().int(),
  disk_read_bytes: z.number().int(),
  uptime: z.number(),
});
export type InstanceInfo = z.infer<typeof InstanceInfoSchema>;

const emptyToUndefined = (v: unknown) => {
  if (v === '' || v === null) {
    return;
  }

  return v;
};

export const VERIFY_MODES = ['none', 'optional', 'required'];

export const SSLParametersSchema = z.object({
  enabled: z.boolean().optional(),
  verify_mode: z.preprocess(
    emptyToUndefined,
    z.enum(VERIFY_MODES).nullable().optional()
  ),
  ca_cert: z.preprocess(emptyToUndefined, z.string().nullable().optional()),
  cert: z.preprocess(emptyToUndefined, z.string().nullable().optional()),
  cert_key: z.preprocess(emptyToUndefined, z.string().nullable().optional()),
});

export const AuthParametersSchema = z.object({
  user: z.preprocess(emptyToUndefined, z.string().min(1).optional()),
  password: z.preprocess(emptyToUndefined, z.string().min(1).optional()),
});

export const ServerParametersSchema = z.object({
  ui_enabled: z.boolean().optional(),
  api_enabled: z.boolean().optional(),
  host: z.preprocess(emptyToUndefined, z.string().min(1).optional()),
  port: z.preprocess(
    emptyToUndefined,
    z.number().int().gte(1).lte(65_535).optional()
  ),
  ssl: SSLParametersSchema.optional(),
  auth: AuthParametersSchema.optional(),
});
export type ServerParameters = z.infer<typeof ServerParametersSchema>;

export const BatchParametersSchema = z.object({
  size: z.preprocess(
    emptyToUndefined,
    z.number().gte(1).int().nullable().optional()
  ),
  delay: z.preprocess(
    emptyToUndefined,
    z.number().gte(0.1).nullable().optional()
  ),
});

const QueueParametersSchema = z.object({
  max_timestamp_batches: z.preprocess(
    emptyToUndefined,
    z.number().int().gte(1).optional()
  ),
  max_event_batches: z.preprocess(
    emptyToUndefined,
    z.number().int().gte(1).optional()
  ),
});
export type QueueParameters = z.infer<typeof QueueParametersSchema>;

export const GenerationParametersSchema = z.object({
  timezone: z.preprocess(emptyToUndefined, z.enum(TIMEZONES).optional()),
  batch: BatchParametersSchema.optional(),
  queue: QueueParametersSchema.optional(),
  keep_order: z.boolean().optional(),
  max_concurrency: z.preprocess(
    emptyToUndefined,
    z.number().int().gte(1).optional()
  ),
  write_timeout: z.preprocess(
    emptyToUndefined,
    z.number().int().gte(1).optional()
  ),
});
export type GenerationParameters = z.infer<typeof GenerationParametersSchema>;

export const LOG_LEVELS = ['debug', 'info', 'warning', 'error', 'critical'];
export const LOG_FORMATS = ['plain', 'json'];

export const LogParametersSchema = z.object({
  level: z.preprocess(emptyToUndefined, z.enum(LOG_LEVELS).optional()),
  format: z.preprocess(emptyToUndefined, z.enum(LOG_FORMATS).optional()),
  max_bytes: z.preprocess(
    emptyToUndefined,
    z.number().int().gte(1024).optional()
  ),
  backups: z.preprocess(emptyToUndefined, z.number().int().gte(1).optional()),
});
export type LogParameters = z.infer<typeof LogParametersSchema>;

export const PathParametersSchema = z.object({
  logs: z.string().min(1),
  startup: z.string().min(1),
  generators_dir: z.string().min(1),
  keyring_cryptfile: z.string().min(1),
  generator_config_filename: z.preprocess(
    emptyToUndefined,
    z.string().min(1).optional()
  ),
});
export type PathParameters = z.infer<typeof PathParametersSchema>;

export const SettingsSchema = z.object({
  server: ServerParametersSchema,
  generation: GenerationParametersSchema,
  log: LogParametersSchema,
  path: PathParametersSchema,
});
export type Settings = z.infer<typeof SettingsSchema>;
