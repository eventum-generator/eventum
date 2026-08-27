import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { EventPluginParams } from './EventPluginTab/EventPluginParams';
import { InputPluginParams } from './InputPluginsTab/InputPluginParams';
import { OutputPluginParams } from './OutputPluginsTab/OutputPluginParams';
import { FileTreeProvider } from './context/FileTreeContext';
import { ProjectNameProvider } from './context/ProjectNameContext';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import {
  EVENT_PLUGIN_DEFAULT_CONFIGS,
  INPUT_PLUGIN_DEFAULT_CONFIGS,
  OUTPUT_PLUGIN_DEFAULT_CONFIGS,
} from '@/api/routes/generator-configs/modules/plugins/registry';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

// A form that picks a file from the project draws nothing until the file
// tree arrives, so without it those forms have no field at all.
const FILE_TREE: FileNode[] = [
  { name: 'generator.yml', is_dir: false, size_in_bytes: 40, children: null },
  {
    name: 'scripts',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'event.py', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
  {
    name: 'templates',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'main.jinja', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

beforeEach(() => {
  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: FILE_TREE,
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);
});

/**
 * Every plugin has a form of its own, and each keeps its own copy of the
 * configuration. Three things have to hold for all of them, and none is
 * visible from a single form:
 *
 * - the form opens on the default configuration without throwing, which
 *   is the state the studio puts it in when a plugin is added;
 * - an edit is reported upwards, under the name of the plugin - the
 *   studio writes what it is handed, so a form that reports nothing
 *   loses the edit and one that reports it under the wrong name writes
 *   a configuration for a different plugin;
 * - the fields the edit did not touch survive it, so editing one value
 *   cannot drop the rest of the configuration.
 *
 * Whether a configuration is valid is not asserted here: a form reports
 * every keystroke, so a half-typed value is invalid by nature. That the
 * defaults themselves parse is asserted where they are defined, in
 * `registry.test.ts`.
 */

const INPUT_NAMES = Object.keys(
  INPUT_PLUGIN_DEFAULT_CONFIGS
) as (keyof typeof INPUT_PLUGIN_DEFAULT_CONFIGS)[];

const EVENT_NAMES = Object.keys(
  EVENT_PLUGIN_DEFAULT_CONFIGS
) as (keyof typeof EVENT_PLUGIN_DEFAULT_CONFIGS)[];

const OUTPUT_NAMES = Object.keys(
  OUTPUT_PLUGIN_DEFAULT_CONFIGS
) as (keyof typeof OUTPUT_PLUGIN_DEFAULT_CONFIGS)[];

/**
 * Mount a form the way the studio does: inside a project, with the file
 * tree of that project available - several forms pick a path from it.
 */
function renderForm(ui: ReactElement) {
  return renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <FileTreeProvider>{ui}</FileTreeProvider>
    </ProjectNameProvider>
  );
}

/**
 * An edit the field will take.
 *
 * Several forms open on a JSON field, which drops anything it cannot
 * parse - and the template parameters field drops anything that is not
 * an object - so a keystroke there reports no change at all. Such a
 * field is recognised by the shape its placeholder shows.
 */
function editFor(field: HTMLInputElement): string {
  const placeholder = field.getAttribute('placeholder') ?? '';

  if (placeholder.startsWith('{')) {
    return '{"a":1}';
  }

  if (placeholder.startsWith('[')) {
    return '["1"]';
  }

  return `${field.value}1`;
}

/**
 * Make one edit in the form and report whether it had a field to make
 * it in.
 *
 * The value is pasted rather than typed: a JSON field holds brackets,
 * which the keyboard reads as key descriptors. The Enter is what
 * commits an entry to a list field, which otherwise holds it as
 * unsubmitted text and reports nothing at all.
 */
async function editFirstField(): Promise<boolean> {
  const boxes = screen.queryAllByRole('textbox');
  const editable = boxes.find((box) => !(box as HTMLInputElement).readOnly) as
    | HTMLInputElement
    | undefined;

  if (editable === undefined) {
    return false;
  }

  const user = userEvent.setup();

  // A field that picks from a list is not edited by typing into it -
  // typing only filters what it offers - so one of the values it offers
  // is chosen instead.
  if (editable.getAttribute('aria-haspopup') === 'listbox') {
    await user.click(editable);

    const option = document.querySelector('[role="option"]');

    if (option === null) {
      return false;
    }

    await user.click(option as HTMLElement);

    return true;
  }

  await user.click(editable);
  await user.clear(editable);
  await user.paste(editFor(editable));
  await user.keyboard('{Enter}');

  return true;
}

/** What one form reported after a single edit. */
async function reportOf(
  name: string,
  form: (onChange: (config: unknown) => void) => ReactElement
): Promise<Record<string, Record<string, unknown>>> {
  const onChange = vi.fn();

  renderForm(form(onChange));

  const edited = await editFirstField();

  expect(edited, `${name}: the form has no field to edit`).toBe(true);
  expect(onChange, `${name}: the form reported no change`).toHaveBeenCalled();

  return onChange.mock.lastCall?.[0] as Record<string, Record<string, unknown>>;
}

/** The keys a configuration held before it was edited. */
function keysOf(config: object): string[] {
  return Object.keys(config).sort((a, b) => a.localeCompare(b));
}

describe('input plugin forms', () => {
  it.each(INPUT_NAMES)('opens on the default config of %s', (name) => {
    const config = { [name]: INPUT_PLUGIN_DEFAULT_CONFIGS[name] };

    renderForm(
      <InputPluginParams
        inputPluginConfig={config as never}
        onChange={vi.fn()}
      />
    );

    expect(screen.getAllByRole('textbox').length).toBeGreaterThan(0);
  });

  it.each(INPUT_NAMES)('reports an edit of %s upwards', async (name) => {
    const config = INPUT_PLUGIN_DEFAULT_CONFIGS[name];
    const reported = await reportOf(name, (onChange) => (
      <InputPluginParams
        inputPluginConfig={{ [name]: config } as never}
        onChange={onChange}
      />
    ));

    expect(Object.keys(reported)).toEqual([name]);
    expect(keysOf(reported[name] ?? {})).toEqual(
      expect.arrayContaining(keysOf(config))
    );
  });
});

describe('event plugin forms', () => {
  it.each(EVENT_NAMES)('opens on the default config of %s', (name) => {
    const config = { [name]: EVENT_PLUGIN_DEFAULT_CONFIGS[name] };

    const { container } = renderForm(
      <EventPluginParams
        eventPluginConfig={config as never}
        onChange={vi.fn()}
      />
    );

    expect(container).not.toBeEmptyDOMElement();
  });

  it.each(EVENT_NAMES)('reports an edit of %s upwards', async (name) => {
    const config = EVENT_PLUGIN_DEFAULT_CONFIGS[name];
    const reported = await reportOf(name, (onChange) => (
      <EventPluginParams
        eventPluginConfig={{ [name]: config } as never}
        onChange={onChange}
      />
    ));

    expect(Object.keys(reported)).toEqual([name]);
    expect(keysOf(reported[name] ?? {})).toEqual(
      expect.arrayContaining(keysOf(config))
    );
  });
});

describe('output plugin forms', () => {
  it.each(OUTPUT_NAMES)('opens on the default config of %s', (name) => {
    const config = { [name]: OUTPUT_PLUGIN_DEFAULT_CONFIGS[name] };

    const { container } = renderForm(
      <OutputPluginParams
        outputPluginConfig={config as never}
        onChange={vi.fn()}
      />
    );

    expect(container).not.toBeEmptyDOMElement();
  });

  it.each(OUTPUT_NAMES)('reports an edit of %s upwards', async (name) => {
    const config = OUTPUT_PLUGIN_DEFAULT_CONFIGS[name];
    const reported = await reportOf(name, (onChange) => (
      <OutputPluginParams
        outputPluginConfig={{ [name]: config } as never}
        onChange={onChange}
      />
    ));

    expect(Object.keys(reported)).toEqual([name]);
    expect(keysOf(reported[name] ?? {})).toEqual(
      expect.arrayContaining(keysOf(config))
    );
  });
});
