import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SamplesParams } from './SamplesParams';
import { useGeneratorFileTree } from '@/api/hooks/useGeneratorConfigs';
import { FileNode } from '@/api/routes/generator-configs/schemas';
import { SampleConfig } from '@/api/routes/generator-configs/schemas/plugins/event/configs/template';
import { FileTreeProvider } from '@/pages/ProjectPage/context/FileTreeContext';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

const FILE_TREE: FileNode[] = [
  {
    name: 'samples',
    is_dir: true,
    size_in_bytes: null,
    children: [
      { name: 'hosts.csv', is_dir: false, size_in_bytes: 20, children: null },
      { name: 'users.json', is_dir: false, size_in_bytes: 20, children: null },
    ],
  },
];

const ITEMS = {
  type: 'items',
  source: ['alpha', 'beta'],
} as unknown as SampleConfig;

function setup(value: SampleConfig = ITEMS) {
  vi.mocked(useGeneratorFileTree).mockReturnValue({
    data: FILE_TREE,
    isLoading: false,
    isError: false,
    isSuccess: true,
    error: null,
  } as unknown as ReturnType<typeof useGeneratorFileTree>);

  const onChange = vi.fn();
  const onDelete = vi.fn();

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <FileTreeProvider>
        <SamplesParams value={value} onChange={onChange} onDelete={onDelete} />
      </FileTreeProvider>
    </ProjectNameProvider>
  );

  return { onChange, onDelete, user: userEvent.setup() };
}

/** What the form last reported. */
function reported(onChange: ReturnType<typeof vi.fn>): SampleConfig {
  return onChange.mock.lastCall?.[0] as SampleConfig;
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A sample is a list held inline, a CSV file or a JSON file, and each
 * kind carries different settings - a delimiter and a header belong to a
 * CSV alone. So changing the kind has to take the settings of the
 * previous one away and seed the ones the new kind needs, or the
 * configuration keeps fields the backend refuses.
 */
describe('SamplesParams', () => {
  it('opens on the kind of sample it was given', () => {
    setup();

    expect(screen.getByRole('radio', { name: 'Items' })).toBeChecked();
    expect(
      screen.getByRole('textbox', { name: /Sample items/ })
    ).toBeInTheDocument();
  });

  it('seeds a CSV with the settings a CSV needs', async () => {
    const { user, onChange } = setup();

    await user.click(screen.getByText('CSV'));

    expect(reported(onChange)).toMatchObject({
      type: 'csv',
      header: true,
      delimiter: ',',
      quotechar: '"',
    });
  });

  it('seeds a list of items with something to start from', async () => {
    const { user, onChange } = setup({
      type: 'csv',
      source: 'samples/hosts.csv',
    } as unknown as SampleConfig);

    await user.click(screen.getByText('Items'));

    expect(reported(onChange)).toMatchObject({
      type: 'items',
      source: ['item1', 'item2', 'item3'],
    });
  });

  it('takes the CSV settings away when the kind changes', async () => {
    const { user, onChange } = setup({
      type: 'csv',
      source: 'samples/hosts.csv',
      header: true,
      delimiter: ',',
      quotechar: '"',
    } as unknown as SampleConfig);

    await user.click(screen.getByText('JSON'));

    const value = reported(onChange) as unknown as Record<string, unknown>;

    expect(value.type).toBe('json');
    expect(value.delimiter).toBeUndefined();
    expect(value.quotechar).toBeUndefined();
    expect(value.header).toBeUndefined();
  });

  it('asks a CSV for its delimiter and header', () => {
    setup({
      type: 'csv',
      source: 'samples/hosts.csv',
      header: true,
      delimiter: ',',
      quotechar: '"',
    } as unknown as SampleConfig);

    expect(
      screen.getByRole('textbox', { name: /Delimiter/ })
    ).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /Header/ })).toBeChecked();
  });

  it('offers a tabulation as a delimiter that cannot be typed', async () => {
    const { user, onChange } = setup({
      type: 'csv',
      source: 'samples/hosts.csv',
      delimiter: ',',
    } as unknown as SampleConfig);

    await user.click(
      screen.getByRole('button', { name: 'Set tabulation as delimiter' })
    );

    expect(reported(onChange)).toMatchObject({ delimiter: '\t' });
  });

  it('asks a JSON sample for nothing but its file', () => {
    setup({
      type: 'json',
      source: 'samples/users.json',
    } as unknown as SampleConfig);

    expect(screen.getByRole('textbox', { name: /Source/ })).toHaveValue(
      'samples/users.json'
    );
    expect(screen.queryByRole('textbox', { name: /Delimiter/ })).toBeNull();
  });

  it('offers the sample to be taken away', async () => {
    const { user, onDelete } = setup();

    await user.click(screen.getByRole('button', { name: 'Remove' }));

    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});
