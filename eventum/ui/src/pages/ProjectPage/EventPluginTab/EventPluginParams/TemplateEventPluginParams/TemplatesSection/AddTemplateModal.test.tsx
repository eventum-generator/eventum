import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AddTemplateModal } from './AddTemplateModal';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

const FILE_TREE: FileNode[] = [
  {
    name: 'templates',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'taken.jinja', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

interface Options {
  existingTemplates?: string[];
  isError?: boolean;
}

function setup(options: Options = {}) {
  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: options.isError === true ? undefined : FILE_TREE,
    isLoading: false,
    isError: options.isError ?? false,
    isSuccess: options.isError !== true,
    error: options.isError === true ? new Error('no tree') : null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);

  const onAdd = vi.fn();

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <AddTemplateModal
        existingTemplates={options.existingTemplates ?? ['access']}
        onAdd={onAdd}
      />
    </ProjectNameProvider>
  );

  return { onAdd, user: userEvent.setup() };
}

function field(label: string): HTMLElement {
  return screen.getByRole('textbox', { name: new RegExp(`^${label}`) });
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Adding a template creates a file and names it in the configuration, so
 * both have to be free: a name another template already answers to would
 * be picked over the wrong one, and a path that exists would be
 * overwritten by the file this creates.
 */
describe('AddTemplateModal', () => {
  it('offers no add until both are given', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  });

  it('hands over the name, the path and the configuration of the template', async () => {
    const { user, onAdd } = setup();

    await user.type(field('Template name'), 'error');
    await user.type(field('File path'), 'templates/error.jinja');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(onAdd).toHaveBeenCalledWith('error', 'templates/error.jinja', {
      template: 'templates/error.jinja',
    });
  });

  it('refuses a name another template already answers to', async () => {
    const { user } = setup({ existingTemplates: ['access'] });

    await user.type(field('Template name'), 'access');

    expect(
      await screen.findByText('Template with this name already exists')
    ).toBeInTheDocument();
  });

  it('refuses a path the project already holds', async () => {
    const { user } = setup();

    // The file would be created over one that is already there.
    await user.type(field('File path'), 'templates/taken.jinja');

    expect(await screen.findByText('File already exists')).toBeInTheDocument();
  });

  it('refuses a file that is not a template', async () => {
    const { user } = setup();

    await user.type(field('File path'), 'templates/error.txt');

    expect(
      await screen.findByText('File extension must be .jinja')
    ).toBeInTheDocument();
  });

  it.each(['tem*plate.jinja', 'a?b.jinja', 'a|b.jinja'])(
    'refuses %s as a path a file cannot carry',
    async (path) => {
      const { user } = setup();

      await user.type(field('File path'), path);

      expect(
        await screen.findByText('File path contains forbidden characters')
      ).toBeInTheDocument();
    }
  );

  it('reports a project it could not read', () => {
    setup({ isError: true });

    // Without the tree it cannot tell a free path from a taken one, so
    // it says so rather than offering a check it cannot make.
    expect(screen.getByText(/Failed/)).toBeInTheDocument();
  });
});
