import { Text } from '@mantine/core';
import { IconChevronRight } from '@tabler/icons-react';
import { FC, Fragment } from 'react';

import { Stage, useStudioConfig, useStudioShell } from './context';

const summarize = (names: string[]): string => {
  if (names.length === 0) {
    return 'empty';
  }
  if (names.length === 1) {
    return names[0]!;
  }
  return `${names[0]} +${names.length - 1}`;
};

export const PipelineStrip: FC = () => {
  const { activeStage, setActiveStage } = useStudioShell();
  const { input, event, output } = useStudioConfig();

  const stages: { key: Stage; label: string; summary: string }[] = [
    { key: 'input', label: 'Input', summary: summarize(input.names) },
    { key: 'event', label: 'Event', summary: event.name ?? 'empty' },
    { key: 'output', label: 'Output', summary: summarize(output.names) },
  ];

  return (
    <div className="studio-pipeline">
      {stages.map((stage, index) => (
        <Fragment key={stage.key}>
          {index > 0 && (
            <IconChevronRight
              size={16}
              className="studio-stage-arrow"
              stroke={2.2}
            />
          )}
          <button
            type="button"
            className="studio-stage"
            data-active={stage.key === activeStage}
            onClick={() => setActiveStage(stage.key)}
          >
            <span className="studio-stage-idx">{index + 1}</span>
            <span>{stage.label}</span>
            <Text span size="xs" c="dimmed" style={{ fontWeight: 400 }}>
              {stage.summary}
            </Text>
          </button>
        </Fragment>
      ))}
    </div>
  );
};
