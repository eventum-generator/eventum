import z from 'zod';

import { GlobalsUsageSchema, ScenarioResponseSchema } from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

import type { GlobalsUsage, ScenarioResponse } from './schemas';

export async function listScenarios(): Promise<string[]> {
  return await validateResponse(
    z.array(z.string()),
    apiClient.get('/scenarios/')
  );
}

export async function getScenario(name: string): Promise<ScenarioResponse> {
  return await validateResponse(
    ScenarioResponseSchema,
    apiClient.get(`/scenarios/${encodeURIComponent(name)}`)
  );
}

export async function deleteScenario(name: string): Promise<void> {
  await apiClient.delete(`/scenarios/${encodeURIComponent(name)}`);
}

export async function addGeneratorToScenario(
  name: string,
  generatorId: string
): Promise<void> {
  await apiClient.post(
    `/scenarios/${encodeURIComponent(name)}/generators/${encodeURIComponent(generatorId)}`
  );
}

export async function removeGeneratorFromScenario(
  name: string,
  generatorId: string
): Promise<void> {
  await apiClient.delete(
    `/scenarios/${encodeURIComponent(name)}/generators/${encodeURIComponent(generatorId)}`
  );
}

export async function getGlobalsUsage(
  scenarioName: string,
  generatorName: string
): Promise<GlobalsUsage> {
  return await validateResponse(
    GlobalsUsageSchema,
    apiClient.get(
      `/scenarios/${encodeURIComponent(scenarioName)}/generators/${encodeURIComponent(generatorName)}/globals-usage`
    )
  );
}

export async function getScenarioGlobalState(
  name: string
): Promise<Record<string, unknown>> {
  return await validateResponse(
    z.record(z.string(), z.unknown()),
    apiClient.get(`/scenarios/${encodeURIComponent(name)}/globals`)
  );
}

export async function updateScenarioGlobalState(
  name: string,
  state: Record<string, unknown>
): Promise<void> {
  await apiClient.patch(
    `/scenarios/${encodeURIComponent(name)}/globals`,
    state
  );
}

export async function clearScenarioGlobalState(name: string): Promise<void> {
  await apiClient.delete(`/scenarios/${encodeURIComponent(name)}/globals`);
}

export async function deleteScenarioGlobalStateKey(
  name: string,
  key: string
): Promise<void> {
  await apiClient.delete(
    `/scenarios/${encodeURIComponent(name)}/globals/${encodeURIComponent(key)}`
  );
}
