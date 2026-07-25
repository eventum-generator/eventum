import {
  Alert,
  Box,
  Button,
  Center,
  Container,
  Image,
  Paper,
  PasswordInput,
  Stack,
  TextInput,
  Title,
} from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { APIError } from '@/api/errors';
import { useLoginMutation } from '@/api/hooks/useAuth';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ROUTE_PATHS } from '@/routing/paths';

export default function SignInPage() {
  const navigate = useNavigate();
  const [commonError, setCommonError] = useState<string | null>(null);

  const loginMutation = useLoginMutation();

  const form = useForm({
    mode: 'uncontrolled',
    initialValues: {
      username: '',
      password: '',
    },
    validate: {
      username: isNotEmpty('Username is required'),
      password: isNotEmpty('Password is required'),
    },
    validateInputOnChange: true,
    onSubmitPreventDefault: 'always',
  });

  function handleSubmit(values: typeof form.values) {
    setCommonError(null);

    loginMutation.mutate(
      {
        username: values.username,
        password: values.password,
      },
      {
        onSuccess: () => {
          void navigate(ROUTE_PATHS.ROOT);
        },
        onError: (error: unknown) => {
          if (error instanceof APIError) {
            setCommonError(error.message);
          } else {
            setCommonError('Unknown error');
          }
        },
      }
    );
  }

  return (
    <Center h="100vh" w="100vw">
      <Container>
        <Paper withBorder w={'400px'}>
          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack m="xl" gap="0">
              <Box ta="center">
                <Image
                  src="/logo.svg"
                  alt="Eventum Logo"
                  h={80}
                  w="auto"
                  fit="contain"
                  mx="auto"
                />
                <Title order={3} ta="center" fw="bold" mt="xs">
                  Sign in to Eventum
                </Title>
              </Box>

              {commonError && (
                <Alert
                  mt="md"
                  variant="default"
                  icon={<AlertIcon variant="error" />}
                >
                  {commonError}
                </Alert>
              )}

              <TextInput
                label="Username"
                withAsterisk
                {...form.getInputProps('username')}
                mt="lg"
              />

              <PasswordInput
                label="Password"
                withAsterisk
                {...form.getInputProps('password')}
                mt="5px"
              />

              <Button
                type="submit"
                fullWidth
                variant="gradient"
                mt="xl"
                mb="xs"
                loading={loginMutation.isPending}
                disabled={loginMutation.isPending}
              >
                Sign In
              </Button>
            </Stack>
          </form>
        </Paper>
      </Container>
    </Center>
  );
}
