import { Container, Stack } from '@mantine/core';

import { ActionsGrid } from './ActionsGrid';
import { HeroCard } from './HeroCard';
import { RecentProjectsSection } from './RecentProjectsSection';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import { useInstanceInfo } from '@/api/hooks/useInstance';

export default function HomePage() {
  const {
    data: instanceInfo,
    isLoading: isInstanceInfoLoading,
    isError: isInstanceInfoError,
  } = useInstanceInfo();

  const { data: generatorDirs } = useGeneratorDirs(true);

  const existingProjectNames = generatorDirs?.map((d) => d.name) ?? [];

  return (
    <Container size="100%">
      <Stack gap="lg">
        <HeroCard
          instanceInfo={instanceInfo}
          isLoading={isInstanceInfoLoading}
          isError={isInstanceInfoError}
        />

        <ActionsGrid existingProjectNames={existingProjectNames} />

        {generatorDirs && (
          <RecentProjectsSection generatorDirs={generatorDirs} />
        )}
      </Stack>
    </Container>
  );
}
