import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FC, useState } from 'react';
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
      { name: 'main.jinja', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

/** The section over a parent that keeps what it reports, as one does. */
const Host: FC<{
  initial?: FormatterConfig;
  onChange: (value: FormatterConfig | undefined) => void;
}> = ({ initial, onChange }) => {
  const [value, setValue] = useState<FormatterConfig | undefined>(initial);

  return (
    <FormatterParams
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
};

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
    <ProjectNameProvider initialProjectName="web">
      <FileTreeProvider>
        <Host initial={value} onChange={onChange} />
      </FileTreeProvider>
    </ProjectNameProvider>
  );

  return { onChange, user: userEvent.setup() };
}

/** Pick a format from the list the field offers. */
async function pickFormat(
  user: ReturnType<typeof userEvent.setup>,
  format: string
) {
  await user.click(screen.getByRole('textbox', { name: /Format/ }));

  const option = [
    ...document.querySelectorAll<HTMLElement>('[role="option"]'),
  ].find((candidate) => candidate.textContent === format);

  if (option === undefined) {
    throw new Error(`no option for ${format}`);
  }

  await user.click(option);
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Every output plugin delivers through a formatter, and each format
 * carries settings of its own - an indent for JSON, a template for the
 * template formats. So the section is the format field plus whatever
 * that format needs, and picking another format must not leave the
 * settings of the previous one behind.
 */
describe('FormatterParams', () => {
  it('offers every format an output can deliver in', async () => {
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

  it('reports the format that was picked', async () => {
    const { user, onChange } = setup();

    await pickFormat(user, 'plain');

    expect(onChange).toHaveBeenCalledWith({ format: 'plain' });
  });

  it('reads a cleared format as no formatter at all', async () => {
    const { user, onChange } = setup({ format: 'plain' } as FormatterConfig);

    // The field carries a clear of its own once it holds a value.
    const clear = document.querySelector<HTMLElement>(
      '.mantine-Select-section button, button.mantine-CloseButton-root'
    );

    expect(clear).not.toBeNull();
    await user.click(clear!);

    // An output without a formatter takes the default of its plugin.
    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it('asks for an indent only where one applies', () => {
    setup({ format: 'json' } as FormatterConfig);

    expect(screen.getByRole('textbox', { name: /Indent/ })).toBeInTheDocument();
  });

  it('asks for no indent where the format has none', () => {
    setup({ format: 'plain' } as FormatterConfig);

    expect(screen.queryByRole('textbox', { name: /Indent/ })).toBeNull();
  });

  it('reports the indent with the format it belongs to', async () => {
    const { user, onChange } = setup({ format: 'json' } as FormatterConfig);

    await user.click(screen.getByRole('textbox', { name: /Indent/ }));
    await user.clear(screen.getByRole('textbox', { name: /Indent/ }));
    await user.paste('4');

    expect(onChange).toHaveBeenLastCalledWith({ format: 'json', indent: 4 });
  });

  it.each(['template', 'template-batch'])(
    'asks for a template for the %s format',
    (format) => {
      setup({ format } as FormatterConfig);

      // The two ways of giving a template are offered as a choice.
      expect(screen.getByRole('radio', { name: 'Template' })).toBeChecked();
      expect(
        screen.getByRole('radio', { name: 'Template file' })
      ).toBeInTheDocument();
    }
  );

  it('takes the template as text', async () => {
    const { user, onChange } = setup({ format: 'template' } as FormatterConfig);

    await user.click(screen.getByPlaceholderText('template code'));
    await user.paste('{{ event }}');

    expect(onChange).toHaveBeenCalledWith({
      format: 'template',
      template: '{{ event }}',
    });
  });

  it('takes the template as a file of the project instead', async () => {
    const { user, onChange } = setup({ format: 'template' } as FormatterConfig);

    await user.click(screen.getByText('Template file'));

    // The two are exclusive - a formatter carries a template or a path
    // to one, never both.
    expect(screen.queryByPlaceholderText('template code')).toBeNull();

    await user.click(screen.getByRole('textbox', { name: /Template path/ }));

    const option = [
      ...document.querySelectorAll<HTMLElement>('[role="option"]'),
    ].find((candidate) => candidate.textContent?.includes('main.jinja'));
    await user.click(option!);

    expect(onChange).toHaveBeenCalledWith({
      format: 'template',
      template_path: 'templates/main.jinja',
    });
  });
});
