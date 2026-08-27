import userEvent from '@testing-library/user-event';
import isEqual from 'lodash/isEqual';
import { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { EventPluginParams } from './EventPluginTab/EventPluginParams';
import { InputPluginParams } from './InputPluginsTab/InputPluginParams';
import { OutputPluginParams } from './OutputPluginsTab/OutputPluginParams';
import { FileTreeProvider } from './context/FileTreeContext';
import { ProjectNameProvider } from './context/ProjectNameContext';
import {
  useGeneratorFileContent,
  useGeneratorFileTree,
} from '@/api/hooks/useGeneratorConfigs';
import {
  EVENT_PLUGIN_DEFAULT_CONFIGS,
  INPUT_PLUGIN_DEFAULT_CONFIGS,
  OUTPUT_PLUGIN_DEFAULT_CONFIGS,
} from '@/api/routes/generator-configs/modules/plugins/registry';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

/**
 * A project holding a file of every kind the forms pick from: a field
 * that offers nothing to pick cannot be edited, and would read as one
 * that is not wired.
 */
const FILE_TREE: FileNode[] = [
  { name: 'generator.yml', is_dir: false, size_in_bytes: 40, children: null },
  {
    name: 'certs',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'ca.pem', is_dir: false, size_in_bytes: 20, children: null },
      { name: 'client.crt', is_dir: false, size_in_bytes: 20, children: null },
      { name: 'client.key', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
  {
    name: 'scripts',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'event.py', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
  {
    name: 'samples',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'events.log', is_dir: false, size_in_bytes: 20, children: null },
      { name: 'hosts.csv', is_dir: false, size_in_bytes: 20, children: null },
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
  {
    name: 'patterns',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'pattern.yml', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

beforeEach(() => {
  // Picking a pattern file opens its editor, which reads that file.
  vi.mocked(useGeneratorFileContent).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileContent>);

  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: FILE_TREE,
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);
});

/**
 * Every field of every plugin form, edited one at a time.
 *
 * A plugin form holds a copy of the configuration and reports what the
 * user changes; a field that is drawn but not wired looks identical to
 * one that works, and the value it shows is simply never written. The
 * forms are wide - Kafka alone draws over twenty fields - so this walks
 * each of them and reads back what the form reported for that field
 * alone.
 *
 * The walk covers the fields wired through the form, which name their
 * path on the control. A handful are wired with a value and an onChange
 * of their own and carry no path; those are covered by the single-edit
 * check in `plugin-params.test.tsx`.
 */

/** A control of a form, and the configuration path it is wired to. */
interface Field {
  path: string;
  element: HTMLElement;
}

function fieldsOf(): Field[] {
  return [...document.querySelectorAll<HTMLElement>('[data-path]')]
    .filter((element) => {
      const input = element as HTMLInputElement;
      return !input.readOnly && !input.disabled;
    })
    .map((element) => ({
      path: element.dataset.path ?? '',
      element,
    }));
}

/**
 * Make an edit the field will take, and report whether one was made.
 *
 * The kind of control decides the gesture: a switch is toggled, a field
 * that picks from a list is picked from, and anything else is typed
 * into - with a value shaped by what its placeholder shows, since a JSON
 * field drops anything it cannot parse and reports nothing at all.
 */
async function edit(
  user: ReturnType<typeof userEvent.setup>,
  element: HTMLElement
): Promise<boolean> {
  const input = element as HTMLInputElement;

  if (input.type === 'checkbox') {
    await user.click(input);
    return true;
  }

  if (input.type === 'radio') {
    // A segmented control hides its radios under the labels it draws,
    // so the label is what can be clicked.
    const label = document.querySelector<HTMLElement>(
      `label[for="${input.id}"]`
    );

    if (label === null) {
      return false;
    }

    await user.click(label);
    return true;
  }

  if (input.getAttribute('aria-haspopup') === 'listbox') {
    await user.click(input);

    // Only the list this field opens is picked from: several fields draw
    // one, and the field names the one it controls. A field that offers
    // nothing to pick from takes free text instead - a list of tags
    // does - so the walk falls through to typing.
    const controls = input.getAttribute('aria-controls');
    const dropdown =
      controls === null ? null : document.querySelector(`#${controls}`);
    const options = [
      ...(dropdown?.querySelectorAll<HTMLElement>('[role="option"]') ?? []),
    ].filter((option) => option.getAttribute('aria-selected') !== 'true');

    if (options.length > 0) {
      await user.click(options[0]!);
      return true;
    }
  }

  if (input.tagName !== 'INPUT' && input.tagName !== 'TEXTAREA') {
    return false;
  }

  // A JSON field drops anything it cannot parse and a list field drops
  // anything that is not one, so the value is shaped by what the
  // placeholder shows. The Enter is what commits an entry to a list.
  const placeholder = input.getAttribute('placeholder') ?? '';
  const value = placeholder.startsWith('{')
    ? '{"a":1}'
    : placeholder.startsWith('[')
      ? '["1"]'
      : `${input.value}1`;

  await user.click(input);

  if (input.value !== '') {
    await user.clear(input);
  }

  await user.paste(value);
  await user.keyboard('{Enter}');

  return true;
}

function renderForm(ui: ReactElement) {
  // A password field offers the secrets of the keyring and a way to the
  // page they are managed on, so the forms navigate.
  return renderWithProviders(
    <MemoryRouter>
      <ProjectNameProvider initialProjectName="web">
        <FileTreeProvider>{ui}</FileTreeProvider>
      </ProjectNameProvider>
    </MemoryRouter>
  );
}

/**
 * Walk every wired field of one form, and return the paths that were
 * edited without the form reporting a configuration it had not reported
 * before.
 *
 * The form is mounted once and the fields are visited in turn, so each
 * edit is read against what the form last reported rather than against
 * what it opened on - mounting afresh per field would multiply the cost
 * of the widest forms by the number of fields they draw.
 */
async function unwiredFields(
  name: string,
  config: object,
  form: (onChange: (config: unknown) => void) => ReactElement
): Promise<string[]> {
  const user = userEvent.setup();
  const onChange = vi.fn();
  const unwired: string[] = [];

  renderForm(form(onChange));

  const paths = fieldsOf().map((field) => field.path);

  expect(
    paths.length,
    `${name}: the form draws no wired field`
  ).toBeGreaterThan(0);

  let last: unknown = config;

  for (const path of paths) {
    const field = fieldsOf().find((candidate) => candidate.path === path);

    if (field === undefined) {
      continue;
    }

    const edited = await edit(user, field.element);

    // A list that stays open after a pick covers whatever is under it,
    // so it is dismissed before the next field is reached.
    await user.keyboard('{Escape}');

    if (!edited) {
      continue;
    }

    const reported = onChange.mock.lastCall?.[0] as
      | Record<string, unknown>
      | undefined;

    // A field that is drawn but not wired reports nothing at all, and
    // one wired to a value the form does not keep reports back what it
    // already held.
    if (reported === undefined || isEqual(reported[name], last)) {
      unwired.push(path);
    } else {
      last = structuredClone(reported[name]);
    }
  }

  return unwired;
}

const INPUT_NAMES = Object.keys(
  INPUT_PLUGIN_DEFAULT_CONFIGS
) as (keyof typeof INPUT_PLUGIN_DEFAULT_CONFIGS)[];

const EVENT_NAMES = Object.keys(
  EVENT_PLUGIN_DEFAULT_CONFIGS
) as (keyof typeof EVENT_PLUGIN_DEFAULT_CONFIGS)[];

const OUTPUT_NAMES = Object.keys(
  OUTPUT_PLUGIN_DEFAULT_CONFIGS
) as (keyof typeof OUTPUT_PLUGIN_DEFAULT_CONFIGS)[];

describe('input plugin fields', () => {
  it.each(INPUT_NAMES)('are all wired in %s', async (name) => {
    const config = INPUT_PLUGIN_DEFAULT_CONFIGS[name];

    const unwired = await unwiredFields(name, config, (onChange) => (
      <InputPluginParams
        inputPluginConfig={{ [name]: config } as never}
        onChange={onChange}
      />
    ));

    expect(unwired).toEqual([]);
  });
});

/**
 * The template form draws every one of its fields itself - parameters,
 * samples and templates are each an editor of its own rather than a
 * field of the plugin - so it names no path for the walk to visit. What
 * it reports is covered by the single-edit check in
 * `plugin-params.test.tsx` and by the browser suite.
 */
const CUSTOM_WIRED = new Set(['template']);

describe('event plugin fields', () => {
  it.each(EVENT_NAMES)('are all wired in %s', async (name) => {
    const config = EVENT_PLUGIN_DEFAULT_CONFIGS[name];

    if (CUSTOM_WIRED.has(name)) {
      const survey = renderForm(
        <EventPluginParams
          eventPluginConfig={{ [name]: config } as never}
          onChange={vi.fn()}
        />
      );

      expect(fieldsOf()).toEqual([]);
      survey.unmount();

      return;
    }

    const unwired = await unwiredFields(name, config, (onChange) => (
      <EventPluginParams
        eventPluginConfig={{ [name]: config } as never}
        onChange={onChange}
      />
    ));

    expect(unwired).toEqual([]);
  });
});

describe('output plugin fields', () => {
  it.each(OUTPUT_NAMES)(
    'are all wired in %s',
    async (name) => {
      const config = OUTPUT_PLUGIN_DEFAULT_CONFIGS[name];

      const unwired = await unwiredFields(name, config, (onChange) => (
        <OutputPluginParams
          outputPluginConfig={{ [name]: config } as never}
          onChange={onChange}
        />
      ));

      expect(unwired).toEqual([]);
    },
    // The widest of these draws two dozen fields, and each is a real
    // interaction - which takes longer than a test is given by default,
    // the more so with coverage instrumenting every keystroke.
    20_000
  );
});
