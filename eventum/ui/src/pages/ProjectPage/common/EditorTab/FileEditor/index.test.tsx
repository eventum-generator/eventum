import { StateEffect } from '@codemirror/state';
import { EditorView } from '@codemirror/view';
import { UseQueryResult } from '@tanstack/react-query';
import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FileEditor } from '.';
import {
  useGeneratorFileContent,
  useGeneratorFileTree,
  usePutGeneratorFileMutation,
} from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';
import { downloadUrl } from '@/utils/download';

vi.mock('@/api/hooks/useGeneratorConfigs', () => ({
  useGeneratorFileTree: vi.fn(),
  useGeneratorFileContent: vi.fn(),
  usePutGeneratorFileMutation: vi.fn(),
}));

vi.mock('@/utils/download', () => ({
  downloadUrl: vi.fn(),
}));

const OVERSIZED_PATH = 'output/events.json';
const OVERSIZED_TREE: FileNode[] = [
  {
    name: 'output',
    is_dir: true,
    size_in_bytes: null,
    children: [
      {
        name: 'events.json',
        is_dir: false,
        size_in_bytes: 12 * 1024 * 1024,
        children: null,
      },
    ],
  },
];

const PROJECT = 'demo';
const FILE_PATH = 'templates/event.json.jinja';
const FILE_CONTENT = '{"event": "first"}\n';

const FILE_TREE: FileNode[] = [
  {
    name: 'templates',
    is_dir: true,
    size_in_bytes: null,
    children: [
      {
        name: 'event.json.jinja',
        is_dir: false,
        size_in_bytes: FILE_CONTENT.length,
        children: null,
      },
    ],
  },
];

function resolved<T>(data: T): UseQueryResult<T, Error> {
  return {
    data,
    isPending: false,
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as UseQueryResult<T, Error>;
}

const save = vi.fn();

beforeEach(() => {
  vi.mocked(useGeneratorFileTree).mockReturnValue(resolved(FILE_TREE));
  vi.mocked(useGeneratorFileContent).mockReturnValue(resolved(FILE_CONTENT));
  vi.mocked(usePutGeneratorFileMutation).mockReturnValue({
    mutate: save,
  } as unknown as ReturnType<typeof usePutGeneratorFileMutation>);
  vi.mocked(downloadUrl).mockClear();
});

function openEditor() {
  const setSaved = vi.fn();

  const { container } = renderWithProviders(
    <ProjectNameProvider initialProjectName={PROJECT}>
      <FileEditor filePath={FILE_PATH} setSaved={setSaved} />
    </ProjectNameProvider>
  );

  const editor = container.querySelector<HTMLElement>('.cm-editor');
  const view = editor === null ? null : EditorView.findFromDOM(editor);

  if (view === null) {
    throw new Error('the editor did not mount');
  }

  return { container, view, setSaved };
}

function typeText(view: EditorView, text: string) {
  for (const character of text) {
    act(() => {
      view.dispatch({
        changes: { from: view.state.doc.length, insert: character },
      });
    });
  }
}

describe('FileEditor', () => {
  it('keeps its configuration while the document is edited', () => {
    // Rebuilding the configuration is the heaviest editor operation short of
    // recreating the view, and whatever an extension keeps in a state field
    // outlives it only while the extension instance stays the same.
    const reconfigure = vi.spyOn(StateEffect.reconfigure, 'of');

    const { view } = openEditor();
    const onMount = reconfigure.mock.calls.length;

    typeText(view, 'edited');

    expect(view.state.doc.toString()).toBe(`${FILE_CONTENT}edited`);
    expect(reconfigure).toHaveBeenCalledTimes(onMount);
  });

  it('reports the file as unsaved on the first edit', () => {
    const { view, setSaved } = openEditor();
    expect(setSaved).not.toHaveBeenCalled();

    typeText(view, 'e');

    expect(setSaved).toHaveBeenCalledWith(false);
  });

  it('opens the search panel on Mod-f', async () => {
    const user = userEvent.setup();
    const { container, view } = openEditor();
    expect(container.querySelector('.ev-cm-search')).toBeNull();

    view.contentDOM.focus();
    await user.keyboard('{Control>}f{/Control}');

    expect(container.querySelector('.ev-cm-search')).toBeInTheDocument();
  });

  it('saves the edited content on Mod-s', async () => {
    const user = userEvent.setup();
    const { view } = openEditor();

    typeText(view, 'edited');
    view.contentDOM.focus();
    await user.keyboard('{Control>}s{/Control}');

    expect(save).toHaveBeenCalledWith(
      {
        name: PROJECT,
        filepath: FILE_PATH,
        content: `${FILE_CONTENT}edited`,
      },
      expect.anything()
    );
  });

  it('offers a file it refuses to open for download instead', async () => {
    const user = userEvent.setup();
    vi.mocked(useGeneratorFileTree).mockReturnValue(resolved(OVERSIZED_TREE));

    renderWithProviders(
      <ProjectNameProvider initialProjectName={PROJECT}>
        <FileEditor filePath={OVERSIZED_PATH} setSaved={vi.fn()} />
      </ProjectNameProvider>
    );

    expect(screen.getByText(/too large to open/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Download' }));

    expect(downloadUrl).toHaveBeenCalledWith(
      '/api/generator-configs/demo/file/output/events.json?download=true',
      'events.json'
    );
  });

  it('does not request the content of a file it refuses to open', () => {
    // Transferring it is what the limit exists to avoid.
    vi.mocked(useGeneratorFileTree).mockReturnValue(resolved(OVERSIZED_TREE));

    renderWithProviders(
      <ProjectNameProvider initialProjectName={PROJECT}>
        <FileEditor filePath={OVERSIZED_PATH} setSaved={vi.fn()} />
      </ProjectNameProvider>
    );

    expect(vi.mocked(useGeneratorFileContent)).toHaveBeenCalledWith(
      PROJECT,
      OVERSIZED_PATH,
      { enabled: false }
    );
  });
});
