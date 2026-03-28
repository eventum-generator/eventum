import { Anchor, Group, Stack, Text } from '@mantine/core';
import { IconBook } from '@tabler/icons-react';
import { FC } from 'react';

import { LINKS } from '@/routing/links';

export const LearnSection: FC = () => {
  return (
    <Stack gap="xs">
      <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
        Learn
      </Text>
      <Stack gap={4}>
        <Anchor
          href={LINKS.DOCUMENTATION}
          target="_blank"
          rel="noopener noreferrer"
          underline="never"
          p="xs"
          style={{
            borderRadius: 'var(--mantine-radius-sm)',
          }}
          styles={{
            root: {
              '&:hover': {
                backgroundColor: 'var(--mantine-color-default-hover)',
              },
            },
          }}
        >
          <Group gap="xs">
            <IconBook size={18} color="var(--mantine-primary-color-filled)" />
            <Text size="sm" c="var(--mantine-color-text)">
              Documentation
            </Text>
          </Group>
        </Anchor>
      </Stack>
    </Stack>
  );
};
