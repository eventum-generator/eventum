import { useMutation, useQueryClient } from '@tanstack/react-query';

import { updateGeneratorInStartup } from '@/api/routes/startup';
import { StartupGeneratorParametersList } from '@/api/routes/startup/schemas';

interface DeleteScenarioVariables {
  scenarioName: string;
  startupEntries: StartupGeneratorParametersList;
}

export function useDeleteScenario() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      scenarioName,
      startupEntries,
    }: DeleteScenarioVariables) => {
      const affectedEntries = startupEntries.filter((entry) =>
        (entry.scenarios ?? []).includes(scenarioName)
      );

      await Promise.all(
        affectedEntries.map((entry) => {
          const updatedScenarios = (entry.scenarios ?? []).filter(
            (s) => s !== scenarioName
          );
          return updateGeneratorInStartup(entry.id, {
            ...entry,
            scenarios: updatedScenarios,
          });
        })
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['startup'],
      });
    },
  });
}
