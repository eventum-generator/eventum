import { S3OutputPluginConfig } from '@/api/routes/generator-configs/schemas/plugins/output/configs/s3';

export const S3OutputPluginDefaultConfig: S3OutputPluginConfig = {
  bucket: 'events',
  endpoint_url: 'http://127.0.0.1:9000',
};
