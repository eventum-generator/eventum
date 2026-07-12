import { Alert, Button, Group, Text } from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconRefresh,
} from '@tabler/icons-react';
import { CSSProperties, FC, useState } from 'react';
import { Link } from 'react-router-dom';

import { CommandBar } from './CommandBar';
import { useStudioShell } from './context';
import { ConsolePanel } from './panels/ConsolePanel';
import { EditorPanel } from './panels/EditorPanel';
import { ExplorerPanel } from './panels/ExplorerPanel';
import { InspectorPanel } from './panels/InspectorPanel';
import './studio.css';
import { useResizable } from './useResizable';
import { ShowErrorDetailsAnchor } from '@/components/ui/ShowErrorDetailsAnchor';
import { ROUTE_PATHS } from '@/routing/paths';

type ConsoleState = 'normal' | 'collapsed' | 'maximized';

export const StudioShell: FC = () => {
  const explorer = useResizable(248, { min: 190, max: 440, axis: 'x' });
  const inspector = useResizable(360, {
    min: 260,
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
  const [consoleState, setConsoleState] = useState<ConsoleState>('normal');
  const { configError, reloadConfig } = useStudioShell();

  // Recovery mode: the config could not be parsed, so the pipeline, inspector
  // and console are unavailable. Keep the file editor so the user can fix the
  // config file that locked them out.
  if (configError) {
    return (
      <div className="studio">
        <Alert
          variant="default"
          icon={<IconAlertTriangle size={18} />}
          title="Generator configuration is invalid"
          styles={{
            root: {
              backgroundColor: 'var(--ev-bad-soft)',
              borderRadius: 'var(--ev-radius)',
            },
            icon: { color: 'var(--ev-bad)' },
            title: { color: 'var(--ev-bad)' },
          }}
        >
          <Text size="sm">
            The generator config could not be loaded, so the pipeline, inspector
            and console are unavailable. Fix the config file in the editor
            below, save it (Ctrl/Cmd+S), then reload.
            <ShowErrorDetailsAnchor error={configError} prependDot />
          </Text>
          <Group mt="sm" gap="xs">
            <Button
              size="xs"
              variant="default"
              leftSection={<IconRefresh size={14} />}
              onClick={reloadConfig}
            >
              Reload project
            </Button>
            <Button
              size="xs"
              variant="subtle"
              component={Link}
              to={ROUTE_PATHS.PROJECTS}
              leftSection={<IconArrowLeft size={14} />}
            >
              Back to projects
            </Button>
          </Group>
        </Alert>

        <div className="studio-body">
          <ExplorerPanel style={{ width: explorer.size, flex: '0 0 auto' }} />
          <div
            className="studio-resizer studio-resizer-col"
            data-dragging={explorer.dragging}
            {...explorer.handleProps}
          />
          <EditorPanel />
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

      <div
        className="studio-body"
        style={consoleState === 'maximized' ? { display: 'none' } : undefined}
      >
        <ExplorerPanel style={{ width: explorer.size, flex: '0 0 auto' }} />
        <div
          className="studio-resizer studio-resizer-col"
          data-dragging={explorer.dragging}
          {...explorer.handleProps}
        />
        <EditorPanel />
        <div
          className="studio-resizer studio-resizer-col"
          data-dragging={inspector.dragging}
          {...inspector.handleProps}
        />
        <InspectorPanel style={{ width: inspector.size, flex: '0 0 auto' }} />
      </div>

      {consoleState === 'normal' && (
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
