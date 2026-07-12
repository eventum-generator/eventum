import { CodeHighlight } from '@mantine/code-highlight';
import { Center, Stack, Text } from '@mantine/core';
import { CSSProperties, FC, ReactNode } from 'react';
import YAML from 'yaml';

import { EventPluginParams } from '../../EventPluginTab/EventPluginParams';
import { InputPluginParams } from '../../InputPluginsTab/InputPluginParams';
import { OutputPluginParams } from '../../OutputPluginsTab/OutputPluginParams';
import {
  EventPluginsList,
  InputPluginsList,
  OutputPluginsList,
} from '../../PluginsList';
import { Stage, useStudioConfig, useStudioShell } from '../context';

const STAGE_TITLE: Record<Stage, string> = {
  input: 'Input plugins',
  event: 'Event plugin',
  output: 'Output plugins',
};

const noop = (): void => {
  /* single event plugin: selection is fixed */
};

const NoPlugin: FC = () => (
  <Center mih={80} p="sm">
    <Text size="sm" c="dimmed">
      No plugin added yet
    </Text>
  </Center>
);

interface SectionProps {
  title: string;
  children: ReactNode;
}

const Section: FC<SectionProps> = ({ title, children }) => (
  <Stack gap="xs" p="sm" className="studio-inspector-section">
    <Text className="studio-inspector-section-title">{title}</Text>
    {children}
  </Stack>
);

const StageBody: FC = () => {
  const { activeStage } = useStudioShell();
  const { config, input, event, output } = useStudioConfig();

  if (activeStage === 'input') {
    const cfg = config.input[input.selected];
    return (
      <>
        <Section title="Plugins">
          <InputPluginsList
            type="input"
            plugins={input.names}
            selectedPlugin={input.selected}
            onChangeSelectedPlugin={input.setSelected}
            onAddNewPlugin={(_, name) => input.add(name)}
            onDeletePlugin={input.remove}
          />
        </Section>
        <Section title="Parameters">
          {cfg ? (
            <InputPluginParams
              key={input.selected}
              inputPluginConfig={cfg}
              onChange={input.change}
            />
          ) : (
            <NoPlugin />
          )}
        </Section>
        {cfg && (
          <Section title="Configuration">
            <CodeHighlight code={YAML.stringify(cfg)} language="yml" />
          </Section>
        )}
      </>
    );
  }

  if (activeStage === 'event') {
    return (
      <>
        <Section title="Plugin">
          <EventPluginsList
            type="event"
            plugins={event.name ? [event.name] : []}
            selectedPlugin={0}
            onChangeSelectedPlugin={noop}
            onAddNewPlugin={(_, name) => event.add(name)}
            onDeletePlugin={() => event.remove()}
            maxPlugins={1}
          />
        </Section>
        <Section title="Parameters">
          {event.config ? (
            <EventPluginParams
              eventPluginConfig={event.config}
              onChange={event.change}
            />
          ) : (
            <NoPlugin />
          )}
        </Section>
        {event.config && (
          <Section title="Configuration">
            <CodeHighlight code={YAML.stringify(event.config)} language="yml" />
          </Section>
        )}
      </>
    );
  }

  const cfg = config.output[output.selected];
  return (
    <>
      <Section title="Plugins">
        <OutputPluginsList
          type="output"
          plugins={output.names}
          selectedPlugin={output.selected}
          onChangeSelectedPlugin={output.setSelected}
          onAddNewPlugin={(_, name) => output.add(name)}
          onDeletePlugin={output.remove}
        />
      </Section>
      <Section title="Parameters">
        {cfg ? (
          <OutputPluginParams
            key={output.selected}
            outputPluginConfig={cfg}
            onChange={output.change}
          />
        ) : (
          <NoPlugin />
        )}
      </Section>
      {cfg && (
        <Section title="Configuration">
          <CodeHighlight code={YAML.stringify(cfg)} language="yml" />
        </Section>
      )}
    </>
  );
};

interface InspectorPanelProps {
  style?: CSSProperties;
}

export const InspectorPanel: FC<InspectorPanelProps> = ({ style }) => {
  const { activeStage } = useStudioShell();
  return (
    <div className="studio-panel studio-inspector" style={style}>
      <div className="studio-panel-header">
        <span>Inspector · {STAGE_TITLE[activeStage]}</span>
      </div>
      <div className="studio-panel-body">
        <StageBody />
      </div>
    </div>
  );
};
