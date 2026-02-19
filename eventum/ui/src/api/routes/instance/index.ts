import { apiClient } from '@/api/client';
import {
  InstanceInfo,
  InstanceInfoSchema,
  Settings,
  SettingsSchema,
} from '@/api/routes/instance/schemas';
import { validateResponse } from '@/api/wrappers';

export async function getInstanceInfo(): Promise<InstanceInfo> {
  return await validateResponse(
    InstanceInfoSchema,
    apiClient.get('/instance/info')
  );
}

export async function getInstanceSettings(): Promise<Settings> {
  return await validateResponse(
    SettingsSchema,
    apiClient.get('/instance/settings')
  );
}

export async function updateInstanceSettings(settings: Settings) {
  await apiClient.put('/instance/settings', settings);
}

export async function stopInstance() {
  await apiClient.post('/instance/stop');
}

export async function restartInstance() {
  await apiClient.post('/instance/restart');
}

export function streamInstanceLogs(endOffset: number): WebSocket {
  const protocol = globalThis.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = globalThis.location.host;

  return new WebSocket(
    `${protocol}://${host}/api/instance/logs/main?end_offset=${endOffset}`
  );
}
