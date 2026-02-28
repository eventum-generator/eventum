import z from 'zod';

import {
  ClickhouseOutputPluginConfigSchema,
  ClickhouseOutputPluginNamedConfigSchema,
} from './configs/clickhouse';
import {
  FileOutputPluginConfigSchema,
  FileOutputPluginNamedConfigSchema,
} from './configs/file';
import {
  HTTPOutputPluginConfigSchema,
  HTTPOutputPluginNamedConfigSchema,
} from './configs/http';
import {
  KafkaOutputPluginConfigSchema,
  KafkaOutputPluginNamedConfigSchema,
} from './configs/kafka';
import {
  OpensearchOutputPluginConfigSchema,
  OpensearchOutputPluginNamedConfigSchema,
} from './configs/opensearch';
import {
  StdoutOutputPluginConfigSchema,
  StdoutOutputPluginNamedConfigSchema,
} from './configs/stdout';
import {
  TcpOutputPluginConfigSchema,
  TcpOutputPluginNamedConfigSchema,
} from './configs/tcp';

export const OutputPluginNamedConfigSchema = z.union([
  ClickhouseOutputPluginNamedConfigSchema,
  FileOutputPluginNamedConfigSchema,
  HTTPOutputPluginNamedConfigSchema,
  KafkaOutputPluginNamedConfigSchema,
  OpensearchOutputPluginNamedConfigSchema,
  StdoutOutputPluginNamedConfigSchema,
  TcpOutputPluginNamedConfigSchema,
]);
export type OutputPluginNamedConfig = z.infer<
  typeof OutputPluginNamedConfigSchema
>;

export const OutputPluginConfigSchema = z.union([
  ClickhouseOutputPluginConfigSchema,
  FileOutputPluginConfigSchema,
  HTTPOutputPluginConfigSchema,
  KafkaOutputPluginConfigSchema,
  OpensearchOutputPluginConfigSchema,
  StdoutOutputPluginConfigSchema,
  TcpOutputPluginConfigSchema,
]);
export type OutputPluginConfig = z.infer<typeof OutputPluginConfigSchema>;
