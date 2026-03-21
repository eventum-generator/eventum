import { GlobalsUsageSchema } from './schemas';
import { apiClient } from '@/api/client';
import { validateResponse } from '@/api/wrappers';

import type { GlobalsUsage } from './schemas';

export async function getGlobalsUsage(
  generatorName: string
): Promise<GlobalsUsage> {
  return await validateResponse(
    GlobalsUsageSchema,
    apiClient.get(`/generator-configs/${generatorName}/globals-usage`)
  );
}
