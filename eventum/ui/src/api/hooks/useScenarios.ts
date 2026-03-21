import { useQueries, useQuery } from '@tanstack/react-query';

import { getGlobalsUsage } from '../routes/scenarios';

export function useGlobalsUsage(generatorName: string) {
  return useQuery({
    queryKey: ['globals-usage', generatorName],
    queryFn: () => getGlobalsUsage(generatorName),
  });
}

export function useMultiGlobalsUsage(generatorNames: string[]) {
  return useQueries({
    queries: generatorNames.map((name) => ({
      queryKey: ['globals-usage', name],
      queryFn: () => getGlobalsUsage(name),
    })),
  });
}
