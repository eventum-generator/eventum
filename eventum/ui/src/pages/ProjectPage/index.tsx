import {
  Alert,
  Anchor,
  Box,
  Center,
  Container,
  Loader,
  Text,
} from '@mantine/core';
import { IconAlertSquareRounded } from '@tabler/icons-react';
import { Link, useParams } from 'react-router-dom';

import { FileTreeProvider } from './context/FileTreeContext';
import { ProjectNameProvider } from './context/ProjectNameContext';
import { StudioProvider } from './studio/StudioProvider';
import { StudioShell } from './studio/StudioShell';
import { APIError } from '@/api/errors';
import { useGeneratorConfig } from '@/api/hooks/useGeneratorConfigs';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

export default function ProjectPage() {
  const { projectName } = useParams() as { projectName: string };

  const {
    data: generatorConfig,
    isSuccess,
    isError,
    error,
    isLoading,
    refetch: refetchConfig,
  } = useGeneratorConfig(projectName);

  if (isLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isError) {
    // A config that cannot be parsed/read (422) or errored on the server (500)
    // still has an editable project directory, so open the studio in recovery
    // mode to let the user fix the file that locked them out. A missing project
    // (404) or other errors have nothing to recover and keep the plain error.
    const status =
      error instanceof APIError ? error.response?.status : undefined;

    if (status === 422 || status === 500) {
      return (
        <ProjectNameProvider initialProjectName={projectName}>
          <FileTreeProvider>
            <StudioProvider
              key="recovery"
              serverConfig={null}
              configError={error}
              onReloadConfig={() => void refetchConfig()}
            >
              <StudioShell />
            </StudioProvider>
          </FileTreeProvider>
        </ProjectNameProvider>
      );
    }

    return (
      <Container size="md">
        <Alert
          variant="default"
          icon={<Box c="red" component={IconAlertSquareRounded}></Box>}
          title="Failed to open project"
        >
          {error.message}
          <ShowErrorDetailsAnchor error={error} prependDot />
          <Anchor component={Link} to={ROUTE_PATHS.PROJECTS}>
            <Text size="sm" ta="end">
              &larr; Go Back
            </Text>
          </Anchor>
        </Alert>
      </Container>
    );
  }

  if (isSuccess) {
    return (
      <ProjectNameProvider initialProjectName={projectName}>
        <FileTreeProvider>
          <StudioProvider key="ready" serverConfig={generatorConfig}>
            <StudioShell />
          </StudioProvider>
        </FileTreeProvider>
      </ProjectNameProvider>
    );
  }

  return null;
}
