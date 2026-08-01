import { Container, Grid, Stack } from '@mantine/core';

import { ExploreNav } from './ExploreNav';
import { MetaFooter } from './MetaFooter';
import { RecentProjects } from './RecentProjects';
import { StatusRail } from './StatusRail';
import { TopBand } from './TopBand';
import { useGeneratorDirs } from '@/api/hooks/useGeneratorConfigs';
import {
  useGenerators,
  useRunningGeneratorsStats,
} from '@/api/hooks/useGenerators';
import { useInstanceInfo } from '@/api/hooks/useInstance';

export default function HomePage() {
  const { data: instanceInfo } = useInstanceInfo();
  const { data: generatorDirs } = useGeneratorDirs(true);
  const { data: generators } = useGenerators();
  const { data: generatorsStats } = useRunningGeneratorsStats();

  const existingProjectNames = generatorDirs?.map((d) => d.name) ?? [];

  return (
    <Container size="100%">
      <Stack gap="xl">
        <TopBand existingProjectNames={existingProjectNames} />

        <Grid gutter="lg">
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Stack gap="lg">
              <RecentProjects generatorDirs={generatorDirs ?? []} />
              <ExploreNav />
            </Stack>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <StatusRail
              generators={generators ?? []}
              generatorsStats={generatorsStats ?? []}
            />
          </Grid.Col>
        </Grid>

        <MetaFooter instanceInfo={instanceInfo} />
      </Stack>
    </Container>
  );
}
