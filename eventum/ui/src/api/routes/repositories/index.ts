import {
  Catalog,
  CatalogSchema,
  Repositories,
  RepositoriesSchema,
  Repository,
} from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

export async function getRepositories(): Promise<Repositories> {
  return await validateResponse(
    RepositoriesSchema,
    apiClient.get('/repositories/')
  );
}

export async function addRepository(repository: Repository) {
  await apiClient.post('/repositories/', repository);
}

export async function deleteRepository(name: string) {
  await apiClient.delete(`/repositories/${encodeURIComponent(name)}`);
}

export async function getCatalog(name: string): Promise<Catalog> {
  return await validateResponse(
    CatalogSchema,
    apiClient.get(`/repositories/${encodeURIComponent(name)}/catalog`)
  );
}

export async function refreshCatalog(name: string): Promise<Catalog> {
  return await validateResponse(
    CatalogSchema,
    apiClient.post(`/repositories/${encodeURIComponent(name)}/refresh`)
  );
}

export async function installGenerator(
  name: string,
  entry: string,
  projectName: string
) {
  await apiClient.post(
    `/repositories/${encodeURIComponent(name)}/catalog/` +
      `${encodeURIComponent(entry)}/install`,
    { name: projectName }
  );
}
