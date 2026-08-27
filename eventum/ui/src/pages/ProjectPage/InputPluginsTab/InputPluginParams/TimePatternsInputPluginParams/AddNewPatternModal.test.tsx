import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import YAML from 'yaml';

import { AddNewPatternModal } from './AddNewPatternModal';
import * as configs from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

const FILE_TREE: FileNode[] = [
  {
    name: 'patterns',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'taken.yml', is_dir: false, size_in_bytes: 40, children: null },
    ],
  },
];

interface Handlers {
  onSuccess?: (data: unknown, variables: { filepath: string }) => void;
  onError?: (error: unknown) => void;
}

function setup(options: { isError?: boolean; failUpload?: boolean } = {}) {
  const mutate = vi.fn(
    (variables: { filepath: string }, handlers: Handlers = {}): void => {
      if (options.failUpload === true) {
        handlers.onError?.(new Error('no space'));
      } else {
        handlers.onSuccess?.(undefined, variables);
      }
    }
  );

  vi.mocked(configs.useUploadGeneratorFileMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as never);
  vi.mocked(configs.useGeneratorFileTree).mockReturnValue({
    data: options.isError === true ? undefined : FILE_TREE,
    isLoading: false,
    isError: options.isError ?? false,
    isSuccess: options.isError !== true,
    error: options.isError === true ? new Error('no tree') : null,
  } as unknown as ReturnType<typeof configs.useGeneratorFileTree>);

  const onAddNewPattern = vi.fn();

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <ModalsProvider>
        <AddNewPatternModal onAddNewPattern={onAddNewPattern} />
      </ModalsProvider>
    </ProjectNameProvider>
  );

  return { mutate, onAddNewPattern, user: userEvent.setup() };
}

function field(): HTMLElement {
  return screen.getByRole('textbox', { name: /File location/ });
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A time pattern is a file of its own, so adding one writes a file and
 * then names it in the plugin. The file has to be new - writing over an
 * existing pattern would replace whatever it held - and it has to be
 * YAML, since that is what the plugin reads.
 */
describe('AddNewPatternModal', () => {
  it('offers no add until a path is given', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled();
  });

  it('writes a pattern the plugin can read, and names it', async () => {
    const { user, mutate, onAddNewPattern } = setup();

    await user.type(field(), 'patterns/business-hours.yml');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    expect(mutate).toHaveBeenCalledWith(
      {
        name: 'web',
        filepath: 'patterns/business-hours.yml',
        content: expect.any(String),
      },
      expect.anything()
    );

    // What it writes has to parse as a pattern, or the editor that opens
    // next cannot read it.
    const content = (
      mutate.mock.calls[0]?.[0] as unknown as { content: string }
    ).content;
    expect(YAML.parse(content)).toMatchObject({
      label: expect.any(String),
      oscillator: expect.any(Object),
      multiplier: expect.any(Object),
      randomizer: expect.any(Object),
      spreader: expect.any(Object),
    });

    expect(onAddNewPattern).toHaveBeenCalledWith('patterns/business-hours.yml');
  });

  it('refuses a path the project already holds', async () => {
    const { user } = setup();

    await user.type(field(), 'patterns/taken.yml');

    expect(await screen.findByText('File already exists')).toBeInTheDocument();
  });

  it('refuses a file that is not YAML', async () => {
    const { user } = setup();

    await user.type(field(), 'patterns/pattern.json');

    expect(
      await screen.findByText('File extension must be .yaml or .yml')
    ).toBeInTheDocument();
  });

  it('names no pattern when the file could not be written', async () => {
    const { user, onAddNewPattern } = setup({ failUpload: true });

    await user.type(field(), 'patterns/business-hours.yml');
    await user.click(screen.getByRole('button', { name: 'Add' }));

    // A pattern named in the plugin without its file would fail the
    // whole configuration on the next read.
    expect(onAddNewPattern).not.toHaveBeenCalled();
  });

  it('reports a project it could not read', () => {
    setup({ isError: true });

    expect(screen.getByText(/Failed/)).toBeInTheDocument();
  });
});
