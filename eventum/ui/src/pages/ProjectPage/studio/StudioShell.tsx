import { CSSProperties, FC, useState } from 'react';

import { CommandBar } from './CommandBar';
import { ConsolePanel } from './panels/ConsolePanel';
import { EditorPanel } from './panels/EditorPanel';
import { ExplorerPanel } from './panels/ExplorerPanel';
import { InspectorPanel } from './panels/InspectorPanel';
import './studio.css';
import { useResizable } from './useResizable';

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
