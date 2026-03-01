import z from 'zod';

import { FormatterConfigSchema } from './formatters';

export type OutputPluginName =
  | 'clickhouse'
  | 'file'
  | 'http'
  | 'kafka'
  | 'opensearch'
  | 'stdout'
  | 'tcp'
  | 'udp';

export const BaseOutputPluginConfigSchema = z.object({
  formatter: FormatterConfigSchema.optional(),
});
