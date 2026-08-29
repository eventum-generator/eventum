import { useForm } from '@mantine/form';
import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TemplatesSection } from './index';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { TemplateEventPluginConfig } from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { FileTreeProvider } from '@/pages/ProjectPage/context/FileTreeContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

const FILE_TREE: FileNode[] = [
  {
    name: 'templates',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'first.jinja', is_dir: false, size_in_bytes: 20, children: null },
      {
        name: 'second.jinja',
        is_dir: false,
        size_in_bytes: 20,
        children: null,
      },
    ],
  },
];

const CONFIG = {
  mode: 'chance',
  templates: [
    { first: { template: 'templates/first.jinja', chance: 70 } },
    { second: { template: 'templates/second.jinja', chance: 30 } },
  ],
} as unknown as TemplateEventPluginConfig;

const Host: FC<{
  initial?: TemplateEventPluginConfig;
  onValues?: (values: TemplateEventPluginConfig) => void;
}> = ({ initial, onValues }) => {
  const form = useForm<TemplateEventPluginConfig>({
    mode: 'uncontrolled',
    initialValues: initial ?? CONFIG,
  });

  return (
    <>
      <TemplatesSection form={form} />
      <button type="button" onClick={() => onValues?.(form.getValues())}>
        read values
      </button>
    </>
  );
};

function setup(
  options: {
    initial?: TemplateEventPluginConfig;
    onValues?: (values: TemplateEventPluginConfig) => void;
  } = {}
) {
  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: FILE_TREE,
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <FileTreeProvider>
        <ModalsProvider>
          <Host initial={options.initial} onValues={options.onValues} />
        </ModalsProvider>
      </FileTreeProvider>
    </ProjectNameProvider>
  );

  return userEvent.setup();
}

/**
 * The list a field offers.
 *
 * Several fields here draw a list, so the one a field controls is read
 * rather than whatever list is in the document.
 */
function optionsOf(field: RegExp): HTMLElement[] {
  const input = screen.getByRole('textbox', { name: field });
  const controls = input.getAttribute('aria-controls');
  const dropdown =
    controls === null ? null : document.querySelector(`#${controls}`);

  return [
    ...(dropdown?.querySelectorAll<HTMLElement>('[role="option"]') ?? []),
  ];
}

/** Pick a value from the list a field offers. */
async function pick(
  user: ReturnType<typeof userEvent.setup>,
  field: RegExp,
  value: string
) {
  await user.click(screen.getByRole('textbox', { name: field }));

  const option = optionsOf(field).find(
    (candidate) => candidate.textContent === value
  );

  if (option === undefined) {
    throw new Error(`no option for ${value}`);
  }

  await user.click(option);
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The picking mode decides what each template of a generator carries: a
 * chance in chance mode, an initial state and transitions in FSM mode, a
 * place in the chain in chain mode. So switching the mode has to take
 * the parameters of the previous one away - a template left holding a
 * chance under FSM is a configuration the backend refuses.
 */
describe('TemplatesSection', () => {
  it('opens on the mode the plugin picks templates by', () => {
    setup();

    // The field shows the name of the mode, not the value it carries.
    expect(
      screen.getByRole('textbox', { name: /Template picking mode/ })
    ).toHaveValue('Chance');
  });

  it('offers every mode a generator can pick by', async () => {
    const user = setup();

    await user.click(
      screen.getByRole('textbox', { name: /Template picking mode/ })
    );

    expect(
      optionsOf(/Template picking mode/).map((option) => option.textContent)
    ).toEqual(['All', 'Any', 'Chance', 'Spin', 'Chain', 'FSM']);
  });

  it('takes the chances away when another mode is picked', async () => {
    let values: TemplateEventPluginConfig | undefined;
    const user = setup({
      onValues: (v) => {
        values = v;
      },
    });

    await pick(user, /Template picking mode/, 'Spin');
    await user.click(screen.getByRole('button', { name: 'read values' }));

    for (const item of values?.templates ?? []) {
      const template = Object.values(item)[0] as { chance?: number };

      expect(template.chance).toBeUndefined();
    }
  });

  it('takes the chain away when another mode is picked', async () => {
    let values: TemplateEventPluginConfig | undefined;
    const user = setup({
      initial: {
        mode: 'chain',
        chain: ['first', 'second'],
        templates: [
          { first: { template: 'templates/first.jinja' } },
          { second: { template: 'templates/second.jinja' } },
        ],
      } as unknown as TemplateEventPluginConfig,
      onValues: (v) => {
        values = v;
      },
    });

    await pick(user, /Template picking mode/, 'Any');
    await user.click(screen.getByRole('button', { name: 'read values' }));

    expect((values as { chain?: string[] }).chain).toBeUndefined();
  });

  it('asks for the order of the chain in chain mode alone', async () => {
    const user = setup();

    expect(screen.queryByRole('textbox', { name: /^Chain/ })).toBeNull();

    await pick(user, /Template picking mode/, 'Chain');

    expect(screen.getByRole('textbox', { name: /^Chain/ })).toBeInTheDocument();
  });

  it('offers the templates of the plugin to put in the chain', async () => {
    const user = setup({
      initial: {
        mode: 'chain',
        templates: CONFIG.templates,
      } as unknown as TemplateEventPluginConfig,
    });

    await user.click(screen.getByRole('textbox', { name: /^Chain/ }));

    expect(optionsOf(/^Chain/).map((option) => option.textContent)).toEqual([
      'first',
      'second',
    ]);
  });

  it('opens the parameters of the template that was picked', async () => {
    const user = setup();

    await pick(user, /Select template to edit/, 'first');

    // Each template carries its own file and, in this mode, its own
    // chance.
    expect(screen.getByRole('textbox', { name: /Chance/ })).toBeInTheDocument();
  });

  it('offers a template to add beside the ones there are', () => {
    setup();

    expect(
      screen.getByRole('button', { name: 'Add new template' })
    ).toBeInTheDocument();
  });
});
