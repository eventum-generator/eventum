import z from 'zod';

import {
  BulkStartResponse,
  BulkStartResponseSchema,
  GeneratorParameters,
  GeneratorParametersSchema,
  GeneratorStats,
  GeneratorStatsSchema,
  GeneratorStatus,
  GeneratorStatusSchema,
  GeneratorsInfo,
  GeneratorsInfoSchema,
} from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

export async function listGenerators(): Promise<GeneratorsInfo> {
  return await validateResponse(
    GeneratorsInfoSchema,
    apiClient.get('/generators/')
  );
}

export async function getGenerator(id: string): Promise<GeneratorParameters> {
  return await validateResponse(
    GeneratorParametersSchema,
    apiClient.get(`/generators/${id}`)
  );
}

export async function addGenerator(id: string, params: GeneratorParameters) {
  await apiClient.post(`/generators/${id}`, params);
}

export async function updateGenerator(id: string, params: GeneratorParameters) {
  await apiClient.put(`/generators/${id}`, params);
}

export async function deleteGenerator(id: string) {
  await apiClient.delete(`/generators/${id}`);
}

export async function getGeneratorStatus(id: string): Promise<GeneratorStatus> {
  return await validateResponse(
    GeneratorStatusSchema,
    apiClient.get(`/generators/${id}/status`)
  );
}

export async function getGeneratorStats(id: string): Promise<GeneratorStats> {
  return await validateResponse(
    GeneratorStatsSchema,
    apiClient.get(`/generators/${id}/stats`)
  );
}

export async function getRunningGeneratorsStats(): Promise<GeneratorStats[]> {
  return await validateResponse(
    z.array(GeneratorStatsSchema),
    apiClient.get('/generators/group-actions/stats-running')
  );
}

export async function startGenerator(id: string) {
  await apiClient.post(`/generators/${id}/start`);
}

export async function stopGenerator(id: string) {
  await apiClient.post(`/generators/${id}/stop`);
}

export async function bulkStartGenerators(
  ids: string[]
): Promise<BulkStartResponse> {
  return await validateResponse(
    BulkStartResponseSchema,
    apiClient.post('/generators/group-actions/bulk-start', ids)
  );
}

export async function bulkStopGenerators(ids: string[]) {
  await apiClient.post('/generators/group-actions/bulk-stop', ids);
}

export async function bulkRemoveGenerators(ids: string[]) {
  await apiClient.post('/generators/group-actions/bulk-delete', ids);
}

export function streamGeneratorLogs(id: string, endOffset: number): WebSocket {
  const protocol = globalThis.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = globalThis.location.host;

  return new WebSocket(
    `${protocol}://${host}/api/generators/${id}/logs?end_offset=${endOffset}`
  );
}
