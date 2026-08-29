import { Alert, SegmentedControl, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { CSSProperties, FC, useState } from 'react';

import { CommandBar } from './CommandBar';
import { useStudioShell } from './context';
import {
  PANEL_MIN_WIDTH,
  StudioPanel,
  WIDE_LAYOUT_QUERY,
  panelStyle,
  resolvePanel,
} from './layout';
import { ConsolePanel } from './panels/ConsolePanel';
import { EditorPanel } from './panels/EditorPanel';
import { ExplorerPanel } from './panels/ExplorerPanel';
import { InspectorPanel } from './panels/InspectorPanel';
import './studio.css';
import { useResizable } from './useResizable';
import { AlertIcon } from '@/components/ui/AlertIcon';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';

type ConsoleState = 'normal' | 'collapsed' | 'maximized';

export const StudioShell: FC = () => {
  const isWideLayout = useMediaQuery(WIDE_LAYOUT_QUERY, true, {
    getInitialValueInEffect: false,
  });

  const explorer = useResizable(248, {
    min: PANEL_MIN_WIDTH.explorer,
    max: 440,
    axis: 'x',
  });
  const inspector = useResizable(360, {
    min: PANEL_MIN_WIDTH.inspector,
    max: 560,
    axis: 'x',
    invert: true,
  });
  const consoleDock = useResizable(320, {
    min: 120,
    max: 720,
    axis: 'y',
    invert: true,
  });
  const [consoleState, setConsoleState] = useState<ConsoleState>(
    // One panel at a time leaves little height to share, and the console is
    // opened on demand rather than read continuously.
    isWideLayout ? 'normal' : 'collapsed'
  );
  const [selectedPanel, setSelectedPanel] = useState<StudioPanel>('editor');
  const { configError } = useStudioShell();

  const hasInspector = !configError;
  const activePanel = isWideLayout
    ? null
    : resolvePanel(selectedPanel, hasInspector);

  const switcher = (
    <SegmentedControl
      fullWidth
      size="xs"
      value={activePanel ?? 'editor'}
      onChange={(value) => setSelectedPanel(value as StudioPanel)}
      data={[
        { label: 'Explorer', value: 'explorer' },
        { label: 'Editor', value: 'editor' },
        ...(hasInspector
          ? [{ label: 'Inspector', value: 'inspector' as const }]
          : []),
      ]}
    />
  );

  // Recovery mode: the config could not be parsed, so the pipeline, inspector
  // and console are unavailable. Keep the command bar (Back + Reload) and the
  // file editor so the user can fix the config file that locked them out.
  if (configError) {
    return (
      <div className="studio">
        <CommandBar />
        <Alert
          variant="default"
          icon={<AlertIcon variant="error" />}
          title="Generator configuration is invalid"
        >
          <Text size="sm">
            The generator config could not be loaded, so the pipeline, inspector
            and console are unavailable. Fix the config file in the editor
            below, save it (Ctrl/Cmd+S), then reload.
            <ShowErrorDetailsAnchor error={configError} prependDot />
          </Text>
        </Alert>

        {activePanel !== null && switcher}

        <div className="studio-body">
          <ExplorerPanel
            style={panelStyle('explorer', {
              active: activePanel,
              size: explorer.size,
            })}
          />
          {isWideLayout && (
            <div
              className="studio-resizer studio-resizer-col"
              data-dragging={explorer.dragging}
              {...explorer.handleProps}
            />
          )}
          <EditorPanel style={panelStyle('editor', { active: activePanel })} />
        </div>
      </div>
    );
  }

  const consoleStyle: CSSProperties =
    consoleState === 'maximized'
      ? { flex: '1 1 auto', minHeight: 0 }
      : consoleState === 'collapsed'
        ? { flex: '0 0 auto' }
        : { height: consoleDock.size, flex: '0 0 auto' };

  return (
    <div className="studio">
      <CommandBar />

      {activePanel !== null && consoleState !== 'maximized' && switcher}

      <div
        className="studio-body"
        style={consoleState === 'maximized' ? { display: 'none' } : undefined}
      >
        <ExplorerPanel
          style={panelStyle('explorer', {
            active: activePanel,
            size: explorer.size,
          })}
        />
        {isWideLayout && (
          <div
            className="studio-resizer studio-resizer-col"
            data-dragging={explorer.dragging}
            {...explorer.handleProps}
          />
        )}
        <EditorPanel style={panelStyle('editor', { active: activePanel })} />
        {isWideLayout && (
          <div
            className="studio-resizer studio-resizer-col"
            data-dragging={inspector.dragging}
            {...inspector.handleProps}
          />
        )}
        <InspectorPanel
          style={panelStyle('inspector', {
            active: activePanel,
            size: inspector.size,
          })}
        />
      </div>

      {/* Dragging a 5px handle is a pointer affordance, so the docks resize
          only in the layout that has a pointer to spare. */}
      {isWideLayout && consoleState === 'normal' && (
        <div
          className="studio-resizer studio-resizer-row"
          data-dragging={consoleDock.dragging}
          {...consoleDock.handleProps}
        />
      )}
      <ConsolePanel
        style={consoleStyle}
        collapsed={consoleState === 'collapsed'}
        maximized={consoleState === 'maximized'}
        onToggleCollapse={() =>
          setConsoleState((s) => (s === 'collapsed' ? 'normal' : 'collapsed'))
        }
        onToggleMaximize={() =>
          setConsoleState((s) => (s === 'maximized' ? 'normal' : 'maximized'))
        }
      />
    </div>
  );
};
