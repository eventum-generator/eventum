import { Box, Flex, Group, Paper, Stack, Text } from '@mantine/core';
import {
  Icon,
  IconArrowRight,
  IconArrowsSplit2,
  IconClockPlay,
  IconCube,
} from '@tabler/icons-react';
import { CSSProperties, FC, Fragment } from 'react';

import { SectionLabel } from './SectionLabel';
import { FlowAgg } from './metrics';
import { useAnimatedNumber } from './useAnimatedNumber';

interface Sub {
  label: string;
  value: string;
  danger?: boolean;
}

interface StageModel {
  name: string;
  value: number;
  unit: string;
  icon: Icon;
  subs: Sub[];
}

const Label: FC<{ icon: Icon; name: string }> = ({ icon: StageIcon, name }) => (
  <Group gap={7} wrap="nowrap" align="center">
    <StageIcon size={15} stroke={1.6} color="var(--ev-muted)" />
    <Text size="xs" tt="uppercase" lts="1.5px" fw={600} c="dimmed">
      {name}
    </Text>
  </Group>
);

const Value: FC<{ value: number; unit: string }> = ({ value, unit }) => {
  const shown = useAnimatedNumber(value);
  return (
    <Group align="baseline" gap={8} wrap="nowrap">
      <Text
        fw={700}
        lh={1}
        style={{
          fontSize: '2.25rem',
          letterSpacing: '-0.02em',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {Math.round(shown).toLocaleString()}
      </Text>
      <Text size="sm" c="dimmed">
        {unit}
      </Text>
    </Group>
  );
};

const Subs: FC<{ subs: Sub[] }> = ({ subs }) => (
  <Group gap="lg" wrap="wrap">
    {subs.map((s) => (
      <Group key={s.label} gap={7} wrap="nowrap" align="center">
        <Text
          size="md"
          fw={700}
          ff="monospace"
          style={{ color: s.danger ? 'var(--ev-bad)' : undefined }}
        >
          {s.value}
        </Text>
        <Text size="sm" c="dimmed">
          {s.label}
        </Text>
      </Group>
    ))}
  </Group>
);

const Arrow: FC<{ col: number }> = ({ col }) => (
  <Flex
    c="var(--ev-faint)"
    style={{ gridColumn: col, gridRow: 2, alignSelf: 'center' }}
  >
    <IconArrowRight size={18} stroke={1.75} />
  </Flex>
);

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr auto 1fr auto 1fr',
  gridTemplateRows: 'auto auto auto',
  columnGap: 'var(--mantine-spacing-md)',
  rowGap: 8,
  alignItems: 'start',
  minWidth: 720,
};

interface PipelineFlowProps {
  flow: FlowAgg;
  inputPlugins: number;
}

export const PipelineFlow: FC<PipelineFlowProps> = ({ flow, inputPlugins }) => {
  const stages: StageModel[] = [
    {
      name: 'Input',
      value: flow.generated,
      unit: 'timestamps enqueued',
      icon: IconClockPlay,
      subs: [
        {
          label: inputPlugins === 1 ? 'input plugin' : 'input plugins',
          value: inputPlugins.toLocaleString(),
        },
      ],
    },
    {
      name: 'Event',
      value: flow.produced,
      unit: 'events produced',
      icon: IconCube,
      subs: [
        { label: 'dropped', value: flow.dropped.toLocaleString() },
        {
          label: 'failed',
          value: flow.produceFailed.toLocaleString(),
          danger: flow.produceFailed > 0,
        },
      ],
    },
    {
      name: 'Output',
      value: flow.written,
      unit: 'events written',
      icon: IconArrowsSplit2,
      subs: [
        {
          label: 'write failed',
          value: flow.writeFailed.toLocaleString(),
          danger: flow.writeFailed > 0,
        },
        {
          label: 'format failed',
          value: flow.formatFailed.toLocaleString(),
          danger: flow.formatFailed > 0,
        },
      ],
    },
  ];

  return (
    <Stack gap="xs">
      <SectionLabel>Pipeline</SectionLabel>
      <Paper withBorder radius="md" p="lg">
        <Box style={{ overflowX: 'auto' }}>
          <div style={gridStyle}>
            {stages.map((st, i) => {
              const col = 2 * i + 1;
              return (
                <Fragment key={st.name}>
                  <Box style={{ gridColumn: col, gridRow: 1 }}>
                    <Label icon={st.icon} name={st.name} />
                  </Box>
                  <Box style={{ gridColumn: col, gridRow: 2 }}>
                    <Value value={st.value} unit={st.unit} />
                  </Box>
                  <Box style={{ gridColumn: col, gridRow: 3 }}>
                    <Subs subs={st.subs} />
                  </Box>
                </Fragment>
              );
            })}
            <Arrow col={2} />
            <Arrow col={4} />
          </div>
        </Box>
      </Paper>
    </Stack>
  );
};
