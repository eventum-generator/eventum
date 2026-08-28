import { act, render, screen } from '@testing-library/react';
import { FC } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { StudioProvider } from './StudioProvider';
import {
  StudioConfigValue,
  StudioShellValue,
  useStudioConfig,
  useStudioShell,
} from './context';
import { useUpdateGeneratorConfigMutation } from '@/api/hooks/useGeneratorConfigs';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { GeneratorConfig } from '@/api/routes/generator-configs/schemas';
import { FileTreeProvider } from '@/pages/ProjectPage/context/FileTreeContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';

vi.mock('@/api/hooks/useGeneratorConfigs');

const CONFIG: GeneratorConfig = {
  input: [{ timer: { seconds: 5, count: 1 } }],
  event: { template: PLUGIN_DEFAULT_CONFIGS.event.template },
  output: [{ file: { path: './output/events.log' } }],
} as GeneratorConfig;

const mutate = vi.fn();

/** Hands the two contexts back so a test can drive them directly. */
let studio: { config: StudioConfigValue; shell: StudioShellValue };

const Probe: FC = () => {
  studio = { config: useStudioConfig(), shell: useStudioShell() };

  return <span>mounted</span>;
};

function setup(
  options: { serverConfig?: GeneratorConfig | null; configError?: Error } = {}
) {
  vi.mocked(useUpdateGeneratorConfigMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as never);

  render(
    <ProjectNameProvider initialProjectName="web">
      <FileTreeProvider>
        <StudioProvider
          serverConfig={options.serverConfig ?? CONFIG}
          configError={options.configError ?? null}
        >
          <Probe />
        </StudioProvider>
      </FileTreeProvider>
    </ProjectNameProvider>
  );

  expect(screen.getByText('mounted')).toBeInTheDocument();
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The provider holds the draft of a generator configuration while it is
 * being edited: what plugin sits at each stage, which one the inspector
 * is on, and whether any of it differs from what the project holds. A
 * plugin is identified by position in the configuration but by identity
 * in the studio - remove the first of two and the second must not be
 * mistaken for it, or the inspector keeps editing a form that now
 * belongs to another plugin.
 */
describe('StudioProvider', () => {
  it('opens on the configuration of the project', () => {
    setup();

    expect(studio.config.config).toEqual(CONFIG);
    expect(studio.config.isConfigDirty).toBe(false);
    expect(studio.config.input.names).toEqual(['timer']);
    expect(studio.config.event.name).toBe('template');
    expect(studio.config.output.names).toEqual(['file']);
  });

  it('adds a plugin with the defaults of that plugin', () => {
    setup();

    act(() => studio.config.input.add('cron'));

    expect(studio.config.input.names).toEqual(['timer', 'cron']);
    expect(studio.config.config.input[1]).toEqual({
      cron: PLUGIN_DEFAULT_CONFIGS.input.cron,
    });
    expect(studio.config.isConfigDirty).toBe(true);
  });

  it('gives every plugin an identity of its own', () => {
    setup();

    act(() => studio.config.input.add('cron'));
    const first = studio.config.input.selectedId;

    act(() => studio.config.input.setSelected(1));

    // The identity is what the inspector keys its form on, so the second
    // plugin must not answer to the first one's.
    expect(studio.config.input.selectedId).not.toBe(first);
  });

  it('writes an edit into the plugin the inspector is on', () => {
    setup();

    act(() => studio.config.input.add('cron'));
    act(() => studio.config.input.setSelected(1));
    act(() =>
      studio.config.input.change({
        cron: { expression: '0 * * * *', count: 3 },
      } as never)
    );

    expect(studio.config.config.input[0]).toEqual(CONFIG.input[0]);
    expect(studio.config.config.input[1]).toEqual({
      cron: { expression: '0 * * * *', count: 3 },
    });
  });

  it('moves the selection off a plugin that was removed', () => {
    setup();

    act(() => studio.config.input.add('cron'));
    act(() => studio.config.input.setSelected(1));
    act(() => studio.config.input.remove(1));

    expect(studio.config.input.names).toEqual(['timer']);
    expect(studio.config.input.selected).toBe(0);
  });

  it('empties the event stage of the studio', () => {
    setup();

    act(() => studio.config.event.remove());

    expect(studio.config.event.name).toBeNull();
    expect(studio.config.event.config).toBeNull();
  });

  // A configuration must name an event plugin, so the draft cannot hold
  // an empty stage: what it holds instead is the default template
  // plugin. Removing a script plugin therefore reads as replacing it
  // with a template, and removing a default template reads as no change
  // at all. Recorded as it behaves.
  it('puts the default template in the draft of an emptied stage', () => {
    setup({
      serverConfig: {
        ...CONFIG,
        event: { script: PLUGIN_DEFAULT_CONFIGS.event.script },
      } as GeneratorConfig,
    });

    act(() => studio.config.event.remove());

    expect(Object.keys(studio.config.config.event)).toEqual(['template']);
    expect(studio.config.isConfigDirty).toBe(true);
  });

  it('reads an emptied default stage as no change', () => {
    setup();

    act(() => studio.config.event.remove());

    expect(studio.config.isConfigDirty).toBe(false);
  });

  it('replaces the event plugin rather than adding to it', () => {
    setup();

    act(() => studio.config.event.add('script'));

    // One stage, one plugin: the previous one is gone rather than kept
    // beside the new one.
    expect(studio.config.event.name).toBe('script');
    expect(Object.keys(studio.config.config.event)).toEqual(['script']);
  });

  it('reads a draft that was edited back to the stored one as clean', () => {
    setup();

    act(() => studio.config.input.add('cron'));
    act(() => studio.config.input.remove(1));

    expect(studio.config.isConfigDirty).toBe(false);
  });

  it('writes the draft the studio holds', () => {
    setup();

    act(() => studio.config.input.add('cron'));
    act(() => studio.config.saveConfig());

    expect(mutate).toHaveBeenCalledWith(
      { name: 'web', config: studio.config.config },
      expect.anything()
    );
  });
});

/**
 * A configuration the backend could not parse puts the studio in
 * recovery mode: the draft it holds is a placeholder, so writing it
 * would overwrite the file the user still has to repair.
 */
describe('StudioProvider in recovery mode', () => {
  it('writes nothing', () => {
    setup({ configError: new Error('generator.yml is not valid YAML') });

    act(() => studio.config.saveConfig());

    expect(mutate).not.toHaveBeenCalled();
  });

  it('reports nothing to save', () => {
    setup({ configError: new Error('generator.yml is not valid YAML') });

    act(() => studio.config.input.add('cron'));

    // The command bar offers a save whenever the draft is dirty, so the
    // draft must never read as dirty here.
    expect(studio.config.isConfigDirty).toBe(false);
  });

  it('carries the error so the shell can draw the recovery layout', () => {
    const error = new Error('generator.yml is not valid YAML');
    setup({ configError: error });

    expect(studio.shell.configError).toBe(error);
  });
});

/**
 * Files are edited in tabs of their own, and each tab registers how it
 * saves itself. The command bar saves everything that is dirty, so the
 * provider is what knows which of them are.
 */
describe('the open files of the studio', () => {
  it('holds no dirty file until one says it is', () => {
    setup();

    expect(studio.shell.dirtyFileIds).toEqual([]);
  });

  it('lists a file that reported an unsaved change', () => {
    setup();

    act(() => studio.shell.setSaved('templates/main.jinja', false));

    expect(studio.shell.dirtyFileIds).toEqual(['templates/main.jinja']);
  });

  it('drops a file from the dirty list once it is saved', () => {
    setup();

    act(() => studio.shell.setSaved('templates/main.jinja', false));
    act(() => studio.shell.setSaved('templates/main.jinja', true));

    expect(studio.shell.dirtyFileIds).toEqual([]);
  });

  it('saves a file through the saver that file registered', () => {
    setup();
    const saver = vi.fn();

    act(() => studio.shell.registerSaver('templates/main.jinja', saver));
    act(() => studio.shell.saveFile('templates/main.jinja'));

    expect(saver).toHaveBeenCalledTimes(1);
  });

  it('saves nothing for a file whose tab is gone', () => {
    setup();
    const saver = vi.fn();

    act(() => studio.shell.registerSaver('templates/main.jinja', saver));
    act(() => studio.shell.unregisterSaver('templates/main.jinja'));
    act(() => studio.shell.saveFile('templates/main.jinja'));

    expect(saver).not.toHaveBeenCalled();
  });

  it('opens on the input stage', () => {
    setup();

    expect(studio.shell.activeStage).toBe('input');
  });

  it('switches the stage the panels follow', () => {
    setup();

    act(() => studio.shell.setActiveStage('output'));

    expect(studio.shell.activeStage).toBe('output');
  });
});
