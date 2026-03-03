import { TcpOutputPluginConfig } from '@/api/routes/generator-configs/schemas/plugins/output/configs/tcp';

export const TcpOutputPluginDefaultConfig: TcpOutputPluginConfig = {
  host: 'localhost',
  port: 514,
};
