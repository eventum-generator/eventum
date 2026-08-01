import {
  SecretNames,
  SecretNamesSchema,
  SecretValue,
  SecretValueSchema,
} from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

export async function getSecretValue(name: string): Promise<SecretValue> {
  return await validateResponse(
    SecretValueSchema,
    apiClient.get(`/secrets/${name}`)
  );
}

export async function getSecretNames(): Promise<SecretNames> {
  return await validateResponse(SecretNamesSchema, apiClient.get(`/secrets/`));
}

export async function setSecretValue(name: string, value: string) {
  await apiClient.put(`/secrets/${name}`, JSON.stringify(value));
}

export async function deleteSecretValue(name: string) {
  await apiClient.delete(`/secrets/${name}`);
}

export async function getSecretReferences(name: string): Promise<SecretNames> {
  return await validateResponse(
    SecretNamesSchema,
    apiClient.get(`/secrets/${encodeURIComponent(name)}/references`)
  );
}

export async function renameSecret(name: string, newName: string) {
  await apiClient.post(`/secrets/${encodeURIComponent(name)}/rename`, {
    new_name: newName,
  });
}
