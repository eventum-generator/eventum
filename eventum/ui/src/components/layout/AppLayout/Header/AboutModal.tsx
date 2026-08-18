import {
  Alert,
  Button,
  Center,
  Divider,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconBox, IconBrandPython, IconServer } from '@tabler/icons-react';
import { FC } from 'react';

import { useInstanceInfo } from '@/api/hooks/useInstance';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ResponsibleCopyButton } from '@/components/ui/ResponsibleCopyButton';
import { describeGilState } from '@/utils/gilState';

export const AboutModal: FC = () => {
  const {
    data: instanceInfo,
    isLoading: isInstanceInfoLoading,
    isSuccess: isInstanceInfoSuccess,
    isError: isInstanceInfoError,
    error: instanceInfoError,
  } = useInstanceInfo();

  if (isInstanceInfoLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isInstanceInfoError) {
    return (
      <Alert
        mt="md"
        variant="default"
        icon={<AlertIcon variant="error" />}
        title="Failed to get instance information"
      >
        {instanceInfoError.message}
      </Alert>
    );
  }

  if (isInstanceInfoSuccess) {
    const gil = describeGilState(instanceInfo);

    return (
      <Stack gap="xs">
        {[
          {
            sectionName: 'Application',
            icon: IconBox,
            sectionItems: [
              { label: 'Version', value: instanceInfo.app_version },
            ],
          },
          {
            sectionName: 'Python',
            icon: IconBrandPython,
            sectionItems: [
              { label: 'Version', value: instanceInfo.python_version },
              {
                label: 'Implementation',
                value: instanceInfo.python_implementation,
              },
              { label: 'Compiler', value: instanceInfo.python_compiler },
              { label: 'Build', value: gil.build },
              { label: 'GIL', value: gil.value },
            ],
          },
          {
            sectionName: 'Server',
            icon: IconServer,
            sectionItems: [
              {
                label: 'Platform',
                value: instanceInfo.platform,
              },
              {
                label: 'Boot time',
                value: new Date(
                  instanceInfo.boot_timestamp * 1000
                ).toLocaleString(),
              },
            ],
          },
        ].map((section) => (
          <Stack gap="4px" mb="xs" key={section.sectionName}>
            <Group gap="xs">
              <section.icon size="19px" />
              <Title order={6} fw={600}>
                {section.sectionName}
              </Title>
            </Group>

            <Divider my="4px" />

            {
              <Stack gap="4px">
                {section.sectionItems.map((sectionItem) => (
                  <Group key={sectionItem.label}>
                    <Text size="sm">
                      {sectionItem.label}: {sectionItem.value}
                    </Text>
                  </Group>
                ))}
              </Stack>
            }
          </Stack>
        ))}
        <Group justify="flex-end" gap="xs">
          <ResponsibleCopyButton
            content={JSON.stringify(instanceInfo, undefined, 2)}
            label="Copy full info"
            tooltipPosition="left"
            size="lg"
          />
          <Button onClick={() => modals.closeAll()} variant="default">
            Close
          </Button>
        </Group>
      </Stack>
    );
  }

  return <></>;
};
