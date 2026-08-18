import {
  Alert,
  Box,
  Button,
  Center,
  CopyButton,
  Divider,
  Group,
  Image,
  Loader,
  Stack,
  Text,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconCheck, IconCopy } from '@tabler/icons-react';
import { FC, ReactNode } from 'react';

import { useInstanceInfo } from '@/api/hooks/useInstance';
import { InstanceInfo } from '@/api/routes/instance/schemas';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { describeGilState } from '@/utils/gilState';

/** The micro-label that names every block of the plate, the version
 *  included. Same recipe as the table headers and the sidebar groups. */
const Eyebrow: FC<{ children: ReactNode }> = ({ children }) => (
  <Text fz="11px" fw={600} lts="0.06em" tt="uppercase" c="dimmed">
    {children}
  </Text>
);

/** One labelled fact. `color` is for the values that carry a state
 *  rather than a constant, `hint` for what that state means. */
const Fact: FC<{
  label: string;
  value: string;
  color?: string;
  hint?: string;
}> = ({ label, value, color, hint }) => (
  <>
    <Text fz="sm" c="dimmed" style={{ lineHeight: 1.7 }}>
      {label}
    </Text>
    <Text
      fz="sm"
      ff="monospace"
      title={hint}
      style={{
        color,
        lineHeight: 1.7,
        wordBreak: 'break-word',
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {value}
    </Text>
  </>
);

/** The heading of a block of facts, spanning both columns of the sheet
 *  so the values below it keep the column the block above them uses. */
const Section: FC<{ title: string; first?: boolean }> = ({ title, first }) => (
  <Box
    style={{
      gridColumn: '1 / -1',
      marginTop: first ? 0 : 'var(--mantine-spacing-lg)',
      marginBottom: '6px',
    }}
  >
    <Eyebrow>{title}</Eyebrow>
  </Box>
);

/** Every fact of the plate on one grid, so the values line up down the
 *  whole sheet rather than per block. The label column takes the width of
 *  its longest label, so the values start right after it instead of
 *  across a fixed gutter. */
const Sheet: FC<{ children: ReactNode }> = ({ children }) => (
  <Box
    style={{
      display: 'grid',
      gridTemplateColumns: 'max-content 1fr',
      columnGap: 'var(--mantine-spacing-lg)',
      rowGap: '2px',
    }}
  >
    {children}
  </Box>
);

/** The identity plate: what this instance is, and what it runs on. Every
 *  block is named by an eyebrow; the version is set large because it is
 *  the fact the dialog is opened for. */
const Plate: FC<{ info: InstanceInfo }> = ({ info }) => {
  const gil = describeGilState(info);

  return (
    <Stack gap="lg">
      <Group gap="md" wrap="nowrap" align="center">
        <Image
          src="/logo.svg"
          alt=""
          h={44}
          w="auto"
          fit="contain"
          draggable={false}
        />
        <Stack gap="2px">
          <Eyebrow>Version</Eyebrow>
          <Text
            ff="monospace"
            fz="28px"
            fw={600}
            lh={1}
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {info.app_version}
          </Text>
        </Stack>
      </Group>

      <Divider />

      <Sheet>
        <Section title="Runtime" first />
        <Fact label="Python" value={info.python_version} />
        <Fact label="Implementation" value={info.python_implementation} />
        <Fact label="Build" value={gil.build} />
        <Fact label="GIL" value={gil.value} color={gil.color} hint={gil.hint} />
        <Fact label="Compiler" value={info.python_compiler} />

        <Section title="Host" />
        <Fact label="Platform" value={info.platform} />
        <Fact
          label="Boot time"
          value={new Date(info.boot_timestamp * 1000).toLocaleString()}
        />
      </Sheet>

      <Divider />

      <Group justify="space-between">
        <CopyButton value={JSON.stringify(info, undefined, 2)}>
          {({ copied, copy }) => (
            <Button
              variant="default"
              onClick={copy}
              leftSection={
                copied ? <IconCheck size={16} /> : <IconCopy size={16} />
              }
            >
              {copied ? 'Copied' : 'Copy details'}
            </Button>
          )}
        </CopyButton>
        <Button variant="default" onClick={() => modals.closeAll()}>
          Close
        </Button>
      </Group>
    </Stack>
  );
};

export const AboutModal: FC = () => {
  const { data: instanceInfo, isLoading, isError, error } = useInstanceInfo();

  if (isLoading) {
    return (
      <Center h={220}>
        <Loader />
      </Center>
    );
  }

  if (isError) {
    return (
      <Alert
        variant="default"
        icon={<AlertIcon variant="error" />}
        title="Failed to get instance information"
      >
        {error.message}
      </Alert>
    );
  }

  if (!instanceInfo) {
    return null;
  }

  return <Plate info={instanceInfo} />;
};
