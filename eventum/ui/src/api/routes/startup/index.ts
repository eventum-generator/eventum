import {
  StartupGeneratorParameters,
  StartupGeneratorParametersList,
  StartupGeneratorParametersListSchema,
  StartupGeneratorParametersSchema,
} from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

export async function getStartupGenerators(): Promise<StartupGeneratorParametersList> {
  return await validateResponse(
    StartupGeneratorParametersListSchema,
    apiClient.get('/startup/')
  );
}

export async function getStartupGenerator(
  id: string
): Promise<StartupGeneratorParameters> {
  return await validateResponse(
    StartupGeneratorParametersSchema,
    apiClient.get(`/startup/${id}`)
  );
}

export async function addGeneratorToStartup(
  id: string,
  params: StartupGeneratorParameters
) {
  await apiClient.post(`/startup/${id}`, params);
}

export async function updateGeneratorInStartup(
  id: string,
  params: StartupGeneratorParameters
) {
  await apiClient.put(`/startup/${id}`, params);
}

export async function deleteGeneratorFromStartup(id: string) {
  await apiClient.delete(`/startup/${id}`);
}

export async function bulkDeleteGeneratorsFromStartup(ids: string[]) {
  await apiClient.post('/startup/group-actions/bulk-delete', ids);
}
