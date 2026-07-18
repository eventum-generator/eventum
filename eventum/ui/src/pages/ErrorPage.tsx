import { Button, Center, Container, Text, Title } from '@mantine/core';

import ErrorSVG from '@/assets/error.svg?react';
import PageIllustration from '@/components/ui/PageIllustration';

export default function ErrorPage({
  error,
  resetError,
}: Readonly<{
  error?: Error;
  resetError?: () => void;
}>) {
  return (
    <Center
      h="100vh"
      w="100vw"
      style={{ flexDirection: 'column', textAlign: 'center' }}
    >
      <Container>
        <PageIllustration SvgComponent={ErrorSVG} />

        <Title order={2} mb="sm">
          Sorry, something went wrong
        </Title>
        <Text size="lg" c="dimmed" mb="md">
          Try reloading the page. If this error keeps happening, please reach
          out to the maintainers.
        </Text>
        <Text size="md" c="dimmed" mb="xl">
          Error info: {error?.message ?? 'no info'}
        </Text>
        <Button size="sm" onClick={resetError}>
          Reload
        </Button>
      </Container>
    </Center>
  );
}
