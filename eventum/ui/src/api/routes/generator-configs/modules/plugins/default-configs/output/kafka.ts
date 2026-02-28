import { KafkaOutputPluginConfig } from '@/api/routes/generator-configs/schemas/plugins/output/configs/kafka';

export const KafkaOutputPluginDefaultConfig: KafkaOutputPluginConfig = {
  bootstrap_servers: ['localhost:9092'],
  topic: 'events',
};
