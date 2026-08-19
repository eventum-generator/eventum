import {
  Catalog,
  CatalogSchema,
  ConnectedRepositories,
  ConnectedRepositoriesSchema,
  Discovery,
  DiscoverySchema,
  Repository,
  RepositoryStatus,
  RepositoryStatusSchema,
} from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

export async function getRepositories(): Promise<ConnectedRepositories> {
  return await validateResponse(
    ConnectedRepositoriesSchema,
    apiClient.get('/repositories/')
  );
}

export async function addRepository(repository: Repository, verify = true) {
  await apiClient.post('/repositories/', repository, { params: { verify } });
}

export async function deleteRepository(name: string) {
  await apiClient.delete(`/repositories/${encodeURIComponent(name)}`);
}

export async function checkRepository(name: string): Promise<RepositoryStatus> {
  return await validateResponse(
    RepositoryStatusSchema,
    apiClient.post(`/repositories/${encodeURIComponent(name)}/check`)
  );
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

export async function discoverRepositories(
  query: string,
  page = 1
): Promise<Discovery> {
  return await validateResponse(
    DiscoverySchema,
    apiClient.get('/repositories/discover', {
      params: { query: query || undefined, page },
    })
  );
}
