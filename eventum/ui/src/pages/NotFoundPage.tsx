import { Button, Center, Container, Title } from '@mantine/core';
import { Link } from 'react-router-dom';

import NotFoundSvg from '@/assets/notFound.svg?react';
import PageIllustration from '@/components/ui/PageIllustration';
import { ROUTE_PATHS } from '@/routing/paths';

export default function NotFound() {
  return (
    <Center
      h="100vh"
      w="100vw"
      flex="column"
      style={{ flexDirection: 'column', textAlign: 'center' }}
    >
      <Container>
        <PageIllustration SvgComponent={NotFoundSvg} />
        <Title order={2} mb="md">
          Page Not Found
        </Title>
        <Button size="md" component={Link} to={ROUTE_PATHS.ROOT}>
          Go Back
        </Button>
      </Container>
    </Center>
  );
}
