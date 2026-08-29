import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import {
  EventStage,
  Stage,
  StudioConfigContext,
  StudioConfigValue,
  StudioShellContext,
  StudioShellValue,
} from '../context';
import { ConsolePanel } from './ConsolePanel';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { renderWithProviders } from '@/test/render';

// The tools the console hosts each talk to the backend and draw with
// measurements jsdom does not take. What is under test here is which of
// them the console shows, so each stands in as its own name.
vi.mock('../../InputPluginsTab/TimestampsHistogram', () => ({
  default: () => <div>timestamps tool</div>,
}));
vi.mock('../../EventPluginTab/Workspace/common/DebuggerTab', () => ({
  DebuggerTab: ({
    onInitializedChange,
  }: {
    onInitializedChange: (value: boolean) => void;
  }) => (
    <button type="button" onClick={() => onInitializedChange(true)}>
      debugger tool
    </button>
  ),
}));
vi.mock(
  '../../EventPluginTab/Workspace/TemplateEventPluginWorkspace/StateTab',
  () => ({ StateTab: () => <div>state tool</div> })
);
vi.mock('../../OutputPluginsTab/FormatterTab', () => ({
  FormatterTab: () => <div>formatter tool</div>,
}));

interface Options {
  stage?: Stage;
  inputPlugins?: number;
  eventPlugin?: 'template' | 'script' | null;
  outputPlugins?: number;
  collapsed?: boolean;
  maximized?: boolean;
  onToggleCollapse?: () => void;
  onToggleMaximize?: () => void;
}

function setup(options: Options = {}) {
  const {
    stage = 'input',
    inputPlugins = 1,
    eventPlugin = 'template',
    outputPlugins = 1,
    collapsed = false,
    maximized = false,
  } = options;

  const eventConfig =
    eventPlugin === null
      ? null
      : ({
          [eventPlugin]: PLUGIN_DEFAULT_CONFIGS.event[eventPlugin],
        } as never);

  const config: StudioConfigValue = {
    config: {
      input: Array.from({ length: inputPlugins }, () => ({
        timer: { seconds: 5, count: 1 },
      })) as never,
      event: eventConfig ?? ({} as never),
      output: Array.from({ length: outputPlugins }, () => ({
        file: { path: './output/events.log' },
      })) as never,
    },
    isConfigDirty: false,
    saveConfig: vi.fn(),
    isSavingConfig: false,
    input: {
      names: Array.from({ length: inputPlugins }, () => 'timer'),
      selected: 0,
      selectedId: 'timer-0',
      setSelected: vi.fn(),
      add: vi.fn(),
      remove: vi.fn(),
      change: vi.fn(),
      getConfig: vi.fn(() => [] as never),
      getSelected: vi.fn(() => 0),
    },
    event: {
      name: eventPlugin,
      config: eventConfig,
      add: vi.fn(),
      remove: vi.fn(),
      change: vi.fn(),
      getConfig: vi.fn(() => eventConfig),
    } as EventStage,
    output: {
      names: Array.from({ length: outputPlugins }, () => 'file'),
      selected: 0,
      selectedId: 'file-0',
      setSelected: vi.fn(),
      add: vi.fn(),
      remove: vi.fn(),
      change: vi.fn(),
    },
  };

  const shell = { activeStage: stage } as StudioShellValue;

  const wrap = (children: ReactNode) => (
    <StudioShellContext.Provider value={shell}>
      <StudioConfigContext.Provider value={config}>
        {children}
      </StudioConfigContext.Provider>
    </StudioShellContext.Provider>
  );

  return renderWithProviders(
    wrap(
      <ConsolePanel
        collapsed={collapsed}
        maximized={maximized}
        onToggleCollapse={options.onToggleCollapse ?? vi.fn()}
        onToggleMaximize={options.onToggleMaximize ?? vi.fn()}
      />
    )
  );
}

/** Whether the pane holding the given tool is the one being shown. */
function paneOf(tool: string): HTMLElement {
  const node = screen.getByText(tool).closest('.stage-pane');

  if (node === null) {
    throw new Error(`${tool} is not inside a pane`);
  }

  return node as HTMLElement;
}

/**
 * Every stage tool stays mounted so it keeps what it holds - a debugger
 * session, a generated preview, a half-filled form - while the user
 * moves between stages. So the console does not mount and unmount the
 * tools, it marks one pane as the active one, and that is what these
 * read. The state view is the one tool that cannot be reached at will:
 * its endpoints answer only for a plugin instance that is running.
 */
describe('ConsolePanel', () => {
  it.each([
    ['input', 'Console · Timestamps preview'],
    ['event', 'Console · Event debugger'],
    ['output', 'Console · Formatter preview'],
  ])('names itself after the %s stage', (stage, title) => {
    setup({ stage: stage as Stage });

    expect(screen.getByText(title)).toBeInTheDocument();
  });

  it('keeps every tool mounted and shows the one of the active stage', () => {
    setup({ stage: 'event' });

    expect(paneOf('timestamps tool')).toHaveAttribute('data-active', 'false');
    expect(paneOf('debugger tool')).toHaveAttribute('data-active', 'true');
    expect(paneOf('formatter tool')).toHaveAttribute('data-active', 'false');
  });

  it.each([
    ['input', 'timestamps tool'],
    ['output', 'formatter tool'],
  ])('shows the tool of the %s stage when it is active', (stage, tool) => {
    setup({ stage: stage as Stage });

    expect(paneOf(tool)).toHaveAttribute('data-active', 'true');
  });

  it('asks for an input plugin instead of a preview of nothing', () => {
    setup({ stage: 'input', inputPlugins: 0 });

    expect(
      screen.getByText('Add an input plugin to preview its timestamps.')
    ).toBeInTheDocument();
    expect(screen.queryByText('timestamps tool')).toBeNull();
  });

  it('asks for an output plugin instead of a formatter preview', () => {
    setup({ stage: 'output', outputPlugins: 0 });

    expect(
      screen.getByText('Add an output plugin to preview formatted events.')
    ).toBeInTheDocument();
  });

  it('asks for an event plugin instead of a debugger', () => {
    setup({ stage: 'event', eventPlugin: null });

    expect(
      screen.getByText('Add an event plugin to debug event production.')
    ).toBeInTheDocument();
    expect(screen.queryByText('debugger tool')).toBeNull();
  });

  it('offers the state view only for the plugin that has one', () => {
    setup({ stage: 'event', eventPlugin: 'script' });

    expect(screen.queryByText('State')).toBeNull();
    expect(screen.getByText('debugger tool')).toBeInTheDocument();
  });

  it('holds the state view back until the debugger is running', async () => {
    const user = userEvent.setup();
    setup({ stage: 'event' });

    // Its endpoints answer for a live plugin instance only, so before
    // one exists the view is offered but cannot be entered.
    expect(screen.getByText('State')).toBeInTheDocument();
    expect(screen.queryByText('state tool')).toBeNull();

    await user.click(screen.getByText('debugger tool'));
    await user.click(screen.getByText('State'));

    expect(paneOf('state tool')).toHaveAttribute('data-active', 'true');
    expect(paneOf('debugger tool')).toHaveAttribute('data-active', 'false');
    expect(screen.getByText('Console · Template state')).toBeInTheDocument();
  });

  it('offers no view switch outside the event stage', () => {
    setup({ stage: 'input' });

    expect(screen.queryByText('Debugger')).toBeNull();
  });

  it('collapses and expands on the control beside the title', async () => {
    const onToggleCollapse = vi.fn();
    const user = userEvent.setup();

    setup({ onToggleCollapse });

    await user.click(screen.getByRole('button', { name: 'Collapse console' }));

    expect(onToggleCollapse).toHaveBeenCalledTimes(1);
  });

  it('maximizes on the control beside the title', async () => {
    const onToggleMaximize = vi.fn();
    const user = userEvent.setup();

    setup({ onToggleMaximize });

    await user.click(screen.getByRole('button', { name: 'Maximize console' }));

    expect(onToggleMaximize).toHaveBeenCalledTimes(1);
  });

  it('offers nothing but expanding while it is collapsed', () => {
    setup({ collapsed: true, stage: 'event' });

    expect(
      screen.queryByRole('button', { name: 'Maximize console' })
    ).toBeNull();
    expect(screen.queryByText('Debugger')).toBeNull();
    expect(
      screen.getByRole('button', { name: 'Collapse console' })
    ).toBeInTheDocument();
  });
});
