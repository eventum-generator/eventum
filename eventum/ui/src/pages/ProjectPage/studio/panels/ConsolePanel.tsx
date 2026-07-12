import { ActionIcon, Group, SegmentedControl, Tooltip } from '@mantine/core';
import {
  IconArrowsMaximize,
  IconArrowsMinimize,
  IconChevronDown,
  IconChevronUp,
} from '@tabler/icons-react';
import { CSSProperties, FC, useState } from 'react';

import { StateTab } from '../../EventPluginTab/Workspace/TemplateEventPluginWorkspace/StateTab';
import { DebuggerTab } from '../../EventPluginTab/Workspace/common/DebuggerTab';
import { GetPluginConfigProvider } from '../../EventPluginTab/context/GetPluginConfigContext';
import TimestampsHistogram from '../../InputPluginsTab/TimestampsHistogram';
import { FormatterTab } from '../../OutputPluginsTab/FormatterTab';
import { EventStage, Stage, useStudioConfig, useStudioShell } from '../context';
import { ToolBody, ToolEmpty } from './console/primitives';

type EventView = 'debugger' | 'state';

const stageTitle = (stage: Stage, eventView: EventView): string => {
  if (stage === 'input') {
    return 'Console · Timestamps preview';
  }
  if (stage === 'output') {
    return 'Console · Formatter preview';
  }
  return eventView === 'state'
    ? 'Console · Template state'
    : 'Console · Event debugger';
};

const StageEmpty: FC<{ message: string }> = ({ message }) => (
  <ToolBody empty>
    <ToolEmpty>{message}</ToolEmpty>
  </ToolBody>
);

interface EventSlotProps {
  active: boolean;
  ready: boolean;
  view: EventView;
  stateAvailable: boolean;
  initialized: boolean;
  onInitializedChange: (value: boolean) => void;
  getConfig: EventStage['getConfig'];
}

/** Both event views stay mounted so the debugger session and the state tables
 *  survive switching between them (and to other stages). */
const EventSlot: FC<EventSlotProps> = ({
  active,
  ready,
  view,
  stateAvailable,
  initialized,
  onInitializedChange,
  getConfig,
}) => {
  if (!ready) {
    return (
      <div className="stage-pane" data-active={active}>
        <StageEmpty message="Add an event plugin to debug event production." />
      </div>
    );
  }

  return (
    <GetPluginConfigProvider getPluginConfig={() => getConfig()!}>
      <div className="stage-pane" data-active={active && view === 'debugger'}>
        <DebuggerTab
          initialized={initialized}
          onInitializedChange={onInitializedChange}
        />
      </div>
      {stateAvailable && (
        <div className="stage-pane" data-active={active && view === 'state'}>
          <StateTab />
        </div>
      )}
    </GetPluginConfigProvider>
  );
};

interface ConsolePanelProps {
  style?: CSSProperties;
  collapsed: boolean;
  maximized: boolean;
  onToggleCollapse: () => void;
  onToggleMaximize: () => void;
}

export const ConsolePanel: FC<ConsolePanelProps> = ({
  style,
  collapsed,
  maximized,
  onToggleCollapse,
  onToggleMaximize,
}) => {
  const { activeStage } = useStudioShell();
  const { config, input, event, output } = useStudioConfig();
  const [eventView, setEventView] = useState<EventView>('debugger');
  const [eventInitialized, setEventInitialized] = useState(false);

  const isTemplate = event.name === 'template';

  // The State view needs a live plugin instance (its endpoints 404 otherwise),
  // so it only becomes reachable once the debugger has been started.
  const stateAvailable = isTemplate && eventInitialized;
  const effectiveEventView: EventView =
    eventView === 'state' && stateAvailable ? 'state' : 'debugger';

  const showEventViewSwitch =
    activeStage === 'event' && event.config !== null && isTemplate;

  return (
    <div
      className="studio-panel studio-console"
      style={style}
      data-collapsed={collapsed}
    >
      <div className="studio-panel-header">
        <span>{stageTitle(activeStage, effectiveEventView)}</span>
        <Group gap={8}>
          {!collapsed && showEventViewSwitch && (
            <SegmentedControl
              size="xs"
              value={effectiveEventView}
              onChange={(value) => setEventView(value as EventView)}
              data={[
                { label: 'Debugger', value: 'debugger' },
                {
                  label: (
                    <Tooltip
                      label="Start the debugger to inspect state"
                      disabled={stateAvailable}
                      withArrow
                    >
                      <span>State</span>
                    </Tooltip>
                  ),
                  value: 'state',
                  disabled: !stateAvailable,
                },
              ]}
            />
          )}
          <Group gap={2}>
            {!collapsed && (
              <Tooltip label={maximized ? 'Restore' : 'Maximize'} withArrow>
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  aria-label="Maximize console"
                  onClick={onToggleMaximize}
                >
                  {maximized ? (
                    <IconArrowsMinimize size={15} />
                  ) : (
                    <IconArrowsMaximize size={15} />
                  )}
                </ActionIcon>
              </Tooltip>
            )}
            <Tooltip label={collapsed ? 'Expand' : 'Collapse'} withArrow>
              <ActionIcon
                variant="subtle"
                size="sm"
                aria-label="Collapse console"
                onClick={onToggleCollapse}
              >
                {collapsed ? (
                  <IconChevronUp size={15} />
                ) : (
                  <IconChevronDown size={15} />
                )}
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </div>

      {/* All stage tools stay mounted; only the active pane is shown, so each
          tool keeps its state (debugger session, generated data, form input)
          when switching stages or views. */}
      <div className="studio-panel-body studio-console-body">
        <div className="stage-pane" data-active={activeStage === 'input'}>
          {config.input.length > 0 ? (
            <TimestampsHistogram
              pluginNames={input.names}
              getInputPluginsConfig={input.getConfig}
            />
          ) : (
            <StageEmpty message="Add an input plugin to preview its timestamps." />
          )}
        </div>

        <EventSlot
          active={activeStage === 'event'}
          ready={event.config !== null}
          view={effectiveEventView}
          stateAvailable={stateAvailable}
          initialized={eventInitialized}
          onInitializedChange={setEventInitialized}
          getConfig={event.getConfig}
        />

        <div className="stage-pane" data-active={activeStage === 'output'}>
          {output.names.length > 0 ? (
            <FormatterTab />
          ) : (
            <StageEmpty message="Add an output plugin to preview formatted events." />
          )}
        </div>
      </div>
    </div>
  );
};
