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
  S3OutputPluginConfigSchema,
  S3OutputPluginNamedConfigSchema,
} from './configs/s3';
import {
  StdoutOutputPluginConfigSchema,
  StdoutOutputPluginNamedConfigSchema,
} from './configs/stdout';
import {
  TcpOutputPluginConfigSchema,
  TcpOutputPluginNamedConfigSchema,
} from './configs/tcp';
import {
  UdpOutputPluginConfigSchema,
  UdpOutputPluginNamedConfigSchema,
} from './configs/udp';

export const OutputPluginNamedConfigSchema = z.union([
  ClickhouseOutputPluginNamedConfigSchema,
  FileOutputPluginNamedConfigSchema,
  HTTPOutputPluginNamedConfigSchema,
  KafkaOutputPluginNamedConfigSchema,
  OpensearchOutputPluginNamedConfigSchema,
  S3OutputPluginNamedConfigSchema,
  StdoutOutputPluginNamedConfigSchema,
  TcpOutputPluginNamedConfigSchema,
  UdpOutputPluginNamedConfigSchema,
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
  S3OutputPluginConfigSchema,
  StdoutOutputPluginConfigSchema,
  TcpOutputPluginConfigSchema,
  UdpOutputPluginConfigSchema,
]);
export type OutputPluginConfig = z.infer<typeof OutputPluginConfigSchema>;
