import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FormatterParams } from './FormatterParams';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { FormatterConfig } from '@/api/routes/generator-configs/schemas/plugins/output/formatters';
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
      { name: 'out.jinja', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

function setup(value?: FormatterConfig) {
  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: FILE_TREE,
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);

  const onChange = vi.fn();

  renderWithProviders(
    <MemoryRouter>
      <ProjectNameProvider initialProjectName="web">
        <FileTreeProvider>
          <FormatterParams value={value} onChange={onChange} />
        </FileTreeProvider>
      </ProjectNameProvider>
    </MemoryRouter>
  );

  return { onChange, user: userEvent.setup() };
}

/** Pick a format from the list the select offers. */
async function pickFormat(
  user: ReturnType<typeof userEvent.setup>,
  format: string
) {
  await user.click(screen.getByRole('textbox', { name: /Format/ }));

  const option = [
    ...document.querySelectorAll<HTMLElement>('[role="option"]'),
  ].find((candidate) => candidate.textContent === format);

  await user.click(option!);
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The formatter decides what an output plugin actually delivers, and
 * each format carries settings of its own - an indent for JSON, a
 * template for the template formats. Those settings only make sense
 * under their format, so picking another one must not leave the previous
 * settings behind: they would travel to the backend under a format that
 * has no field for them.
 */
describe('FormatterParams', () => {
  it('offers every format the plugins deliver', async () => {
    const { user } = setup();

    await user.click(screen.getByRole('textbox', { name: /Format/ }));

    expect(
      [...document.querySelectorAll('[role="option"]')].map(
        (option) => option.textContent
      )
    ).toEqual([
      'eventum-http-input',
      'json',
      'json-batch',
      'plain',
      'template',
      'template-batch',
    ]);
  });

  it.each(['json', 'plain', 'template'])(
    'reports %s as the format that was picked',
    async (format) => {
      const { user, onChange } = setup();

      await pickFormat(user, format);

      expect(onChange).toHaveBeenCalledWith({ format });
    }
  );

  it('drops the formatter when the format is cleared', async () => {
    const { user, onChange } = setup({ format: 'json' } as FormatterConfig);

    // The clear of a Mantine select is an unnamed button inside the
    // field, so it is reached through the section it clears.
    const clear = document.querySelector<HTMLElement>(
      '.mantine-Select-section button, .mantine-CloseButton-root'
    );
    await user.click(clear!);

    // No formatter at all is a value the plugin takes; a format of
    // nothing is not.
    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it.each(['json', 'json-batch'])('offers an indent for %s', (format) => {
    setup({ format } as FormatterConfig);

    expect(screen.getByRole('textbox', { name: /Indent/ })).toBeVisible();
  });

  it.each(['plain', 'template'])('offers no indent for %s', (format) => {
    setup({ format } as FormatterConfig);

    expect(screen.queryByRole('textbox', { name: /Indent/ })).toBeNull();
  });

  it.each(['template', 'template-batch'])(
    'takes a template written in place for %s',
    async (format) => {
      const { user, onChange } = setup({ format } as FormatterConfig);

      await user.click(screen.getByRole('textbox', { name: /^Template/ }));
      await user.paste('{{ event }}');

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ format, template: '{{ event }}' })
      );
    }
  );

  it('takes a template read from a file of the project instead', async () => {
    const { user, onChange } = setup({ format: 'template' } as FormatterConfig);

    await user.click(screen.getByText('Template file'));
    await user.click(screen.getByRole('textbox', { name: /Template path/ }));

    const option = [
      ...document.querySelectorAll<HTMLElement>('[role="option"]'),
    ].find((candidate) => candidate.textContent?.includes('out.jinja'));
    await user.click(option!);

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'template' })
    );
  });

  it('offers nothing but the format until one is picked', () => {
    setup();

    expect(screen.getByRole('textbox', { name: /Format/ })).toBeVisible();
    expect(screen.queryByRole('textbox', { name: /Indent/ })).toBeNull();
    expect(screen.queryByRole('textbox', { name: /^Template/ })).toBeNull();
  });
});
