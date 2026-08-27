import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';

import { StateTab } from './index';
import * as preview from '@/api/hooks/usePreview';
import { PLUGIN_DEFAULT_CONFIGS } from '@/api/routes/generator-configs/modules/plugins/registry';
import { EventPluginNamedConfig } from '@/api/routes/generator-configs/schemas/plugins/event';
import { GetPluginConfigProvider } from '@/pages/ProjectPage/EventPluginTab/context/GetPluginConfigContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/usePreview');

const CONFIG = {
  template: {
    ...PLUGIN_DEFAULT_CONFIGS.event.template,
    templates: [
      { first: { template: 'templates/first.jinja' } },
      { second: { template: 'templates/second.jinja' } },
    ],
  },
} as unknown as EventPluginNamedConfig;

/** A query the tab reads a state scope through. */
function query(data: Record<string, unknown>) {
  return {
    data,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof preview.useTemplateEventPluginSharedState>;
}

/**
 * A mutation the tab writes a state scope through.
 *
 * The nine calls differ in what they take - a template alias for the
 * local scope, a key for a deletion - so the stand-in is untyped and the
 * assertions name the arguments each one is expected to receive.
 */
function mutation(): { mutate: Mock; isPending: boolean } {
  return { mutate: vi.fn(), isPending: false };
}

const MUTATIONS = {
  updateLocal: mutation(),
  deleteLocal: mutation(),
  clearLocal: mutation(),
  updateShared: mutation(),
  deleteShared: mutation(),
  clearShared: mutation(),
  updateGlobal: mutation(),
  deleteGlobal: mutation(),
  clearGlobal: mutation(),
};

/**
 * The stand-ins as the hooks declare them. Each of the nine takes
 * arguments of its own, so the cast happens once here rather than at
 * every call site.
 */
const MUTATIONS_AS_HOOKS = MUTATIONS as unknown as Record<
  keyof typeof MUTATIONS,
  never
>;

function setup(
  states: {
    local?: Record<string, unknown>;
    shared?: Record<string, unknown>;
    global?: Record<string, unknown>;
  } = {}
) {
  vi.mocked(preview.useTemplateEventPluginLocalState).mockReturnValue(
    query(states.local ?? { attempt: 3 })
  );
  vi.mocked(preview.useTemplateEventPluginSharedState).mockReturnValue(
    query(states.shared ?? { session: 'abc' })
  );
  vi.mocked(preview.useTemplateEventPluginGlobalState).mockReturnValue(
    query(states.global ?? { fleet: 12 })
  );

  vi.mocked(
    preview.useUpdateTemplateEventPluginLocalStateMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.updateLocal);
  vi.mocked(
    preview.useDeleteTemplateEventPluginLocalStateKeyMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.deleteLocal);
  vi.mocked(
    preview.useClearTemplateEventPluginLocalStateMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.clearLocal);
  vi.mocked(
    preview.useUpdateTemplateEventPluginSharedStateMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.updateShared);
  vi.mocked(
    preview.useDeleteTemplateEventPluginSharedStateKeyMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.deleteShared);
  vi.mocked(
    preview.useClearTemplateEventPluginSharedStateMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.clearShared);
  vi.mocked(
    preview.useUpdateTemplateEventPluginGlobalStateMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.updateGlobal);
  vi.mocked(
    preview.useDeleteTemplateEventPluginGlobalStateKeyMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.deleteGlobal);
  vi.mocked(
    preview.useClearTemplateEventPluginGlobalStateMutation
  ).mockReturnValue(MUTATIONS_AS_HOOKS.clearGlobal);

  return renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <GetPluginConfigProvider getPluginConfig={() => CONFIG}>
        <ModalsProvider>
          <StateTab />
        </ModalsProvider>
      </GetPluginConfigProvider>
    </ProjectNameProvider>
  );
}

/**
 * The pane of one scope, addressed by the heading it carries.
 *
 * The three panes hold the same controls under the same names, so every
 * assertion runs inside one of them.
 */
function pane(title: string): HTMLElement {
  const heading = screen.getByRole('heading', { name: title });
  const node = heading.closest('.tool-pane');

  if (node === null) {
    throw new Error(`${title} has no pane`);
  }

  return node as HTMLElement;
}

/** Confirm the dialog a destructive action opened. */
async function confirm(
  user: ReturnType<typeof userEvent.setup>,
  label: string
) {
  const dialog = await screen.findByRole('dialog');
  await user.click(within(dialog).getByRole('button', { name: label }));
}

/** Pick a template so its local state is read. */
async function pickTemplate(
  user: ReturnType<typeof userEvent.setup>,
  name: string
) {
  await user.click(screen.getByRole('textbox', { name: /Template/ }));

  const option = [
    ...document.querySelectorAll<HTMLElement>('[role="option"]'),
  ].find((element) => element.textContent === name);

  if (option === undefined) {
    throw new Error(`no option for ${name}`);
  }

  await user.click(option);
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The tab holds the three scopes a template writes into, and each is a
 * different reach: one template, one generator, the whole process. They
 * are read and written through nine calls of their own, so a pane wired
 * to the wrong one would still look right - the state of another scope
 * is state all the same. Each check therefore names the call it expects.
 */
describe('StateTab', () => {
  it('holds a pane per scope', () => {
    setup();

    expect(screen.getByRole('heading', { name: 'Shared state' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Global state' })).toBeVisible();
  });

  it('asks for a template before reading a local state', () => {
    setup();

    // A local state belongs to one template, so there is nothing to
    // read until one is named.
    expect(
      screen.getByText('Select a template to inspect its local state.')
    ).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Local state' })).toBeNull();
  });

  it('offers the templates the plugin declares', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('textbox', { name: /Template/ }));

    const options = [...document.querySelectorAll('[role="option"]')].map(
      (element) => element.textContent
    );

    expect(options).toEqual(['first', 'second']);
  });

  it('reads the local state of the template that was picked', async () => {
    const user = userEvent.setup();
    setup();

    await pickTemplate(user, 'first');

    expect(screen.getByRole('heading', { name: 'Local state' })).toBeVisible();
    expect(within(pane('Local state')).getByText('attempt')).toBeVisible();
  });

  it('shows the keys of every scope it read', () => {
    setup();

    expect(within(pane('Shared state')).getByText('session')).toBeVisible();
    expect(within(pane('Global state')).getByText('fleet')).toBeVisible();
  });

  it('says that the global scope reaches beyond this generator', () => {
    setup();

    expect(
      within(pane('Global state')).getByText('Shared across generators')
    ).toBeVisible();
  });

  it('clears the shared scope through the shared call alone', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(
      within(pane('Shared state')).getByRole('button', { name: 'Clear all' })
    );
    await confirm(user, 'Clear all');

    expect(MUTATIONS.clearShared.mutate).toHaveBeenCalledWith(
      { name: 'web' },
      expect.anything()
    );
    expect(MUTATIONS.clearGlobal.mutate).not.toHaveBeenCalled();
    expect(MUTATIONS.clearLocal.mutate).not.toHaveBeenCalled();
  });

  it('clears the global scope through the global call alone', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(
      within(pane('Global state')).getByRole('button', { name: 'Clear all' })
    );
    await confirm(user, 'Clear all');

    expect(MUTATIONS.clearGlobal.mutate).toHaveBeenCalledWith(
      { name: 'web' },
      expect.anything()
    );
    expect(MUTATIONS.clearShared.mutate).not.toHaveBeenCalled();
  });

  it('clears a local state under the template it belongs to', async () => {
    const user = userEvent.setup();
    setup();

    await pickTemplate(user, 'second');
    await user.click(
      within(pane('Local state')).getByRole('button', { name: 'Clear all' })
    );
    await confirm(user, 'Clear all');

    expect(MUTATIONS.clearLocal.mutate).toHaveBeenCalledWith(
      { name: 'web', templateAlias: 'second' },
      expect.anything()
    );
  });

  it('deletes a key of the scope it was deleted from', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(
      within(pane('Global state')).getByRole('button', { name: 'Key actions' })
    );
    await user.click(await screen.findByText('Delete'));
    await confirm(user, 'Delete');

    expect(MUTATIONS.deleteGlobal.mutate).toHaveBeenCalledWith(
      { name: 'web', key: 'fleet' },
      expect.anything()
    );
    expect(MUTATIONS.deleteShared.mutate).not.toHaveBeenCalled();
  });
});
