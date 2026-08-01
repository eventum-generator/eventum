import {
  Alert,
  Button,
  Center,
  Code,
  Collapse,
  Container,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { NewSecretForm } from './NewSecretForm';
import SecretRow from './SecretRow';
import { SecretsEmptyState } from './SecretsEmptyState';
import { useSecretNames } from '@/api/hooks/useSecrets';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { PageTitle } from '@/components/ui/PageTitle';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

export default function SecretsPage() {
  const [isAdding, setAdding] = useState(false);

  const {
    data: secretNames,
    isLoading: isSecretNamesLoading,
    isError: isSecretNamesError,
    error: secretNamesError,
    isSuccess: isSecretNamesSuccess,
  } = useSecretNames();

  if (isSecretNamesLoading) {
    return (
      <Center>
        <Loader size="lg" />
      </Center>
    );
  }

  if (isSecretNamesError) {
    return (
      <Container size="md" mt="lg">
        <PageTitle title="Secrets" />
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Failed to load list of secrets"
        >
          {secretNamesError.message}
          <ShowErrorDetailsAnchor error={secretNamesError} prependDot />
        </Alert>
      </Container>
    );
  }

  if (isSecretNamesSuccess) {
    const count = secretNames.length;

    return (
      <Container size="xl" mb="400px">
        <Stack>
          <PageTitle title="Secrets" />

          {count === 0 && !isAdding ? (
            <SecretsEmptyState onAdd={() => setAdding(true)} />
          ) : (
            <>
              <Alert variant="default" icon={<AlertIcon variant="info" />}>
                <Text size="sm">
                  Secrets are stored in the keyring and referenced in
                  configuration as <Code>{'${secrets.name}'}</Code>.
                </Text>
              </Alert>

              <Paper withBorder p="sm">
                <Stack gap="sm">
                  <Group justify="space-between" align="center">
                    <Text size="sm" c="dimmed">
                      {count} {count === 1 ? 'secret' : 'secrets'}
                    </Text>
                    <Button
                      variant="subtle"
                      leftSection={<IconPlus size={16} />}
                      onClick={() => setAdding(true)}
                      disabled={isAdding}
                    >
                      Add secret
                    </Button>
                  </Group>

                  <Collapse in={isAdding}>
                    <NewSecretForm onCancel={() => setAdding(false)} />
                  </Collapse>

                  {count > 0 && (
                    <Table stickyHeader stickyHeaderOffset={60}>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th w="40%">Name</Table.Th>
                          <Table.Th>Value</Table.Th>
                          <Table.Th
                            style={{
                              width: '1%',
                              whiteSpace: 'nowrap',
                              textAlign: 'right',
                            }}
                          >
                            Actions
                          </Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {secretNames.map((item) => (
                          <SecretRow
                            key={item}
                            name={item}
                            existingNames={secretNames}
                          />
                        ))}
                      </Table.Tbody>
                    </Table>
                  )}
                </Stack>
              </Paper>
            </>
          )}
        </Stack>
      </Container>
    );
  }

  return <></>;
}
