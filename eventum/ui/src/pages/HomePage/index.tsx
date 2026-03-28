import { Container, SimpleGrid, Stack } from '@mantine/core';

import { BrowseSection } from './BrowseSection';
import { HeroCard } from './HeroCard';
import { LearnSection } from './LearnSection';
import { RecentProjectsSection } from './RecentProjectsSection';
import { StartSection } from './StartSection';
import { useGenerators } from '@/api/hooks/useGenerators';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { useScenarios } from '@/api/hooks/useScenarios';

export default function HomePage() {
  const {
    data: instanceInfo,
    isLoading: isInstanceInfoLoading,
    isError: isInstanceInfoError,
  } = useInstanceInfo();

  const { data: generators } = useGenerators();

  const { data: scenarios } = useScenarios();

  const existingProjectNames = generators?.map((g) => g.id) ?? [];

  return (
    <Container size="md" py="xl">
      <Stack gap="xl">
        <HeroCard
          instanceInfo={instanceInfo}
          isLoading={isInstanceInfoLoading}
          isError={isInstanceInfoError}
        />

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xl">
          <StartSection existingProjectNames={existingProjectNames} />
          <BrowseSection
            generators={generators}
            scenarioCount={scenarios?.length}
          />
          <LearnSection />
        </SimpleGrid>

        {generators && <RecentProjectsSection generators={generators} />}
      </Stack>
    </Container>
  );
}
