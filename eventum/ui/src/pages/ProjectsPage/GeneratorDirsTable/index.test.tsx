import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GeneratorDirsTable, UsageMode } from './index';
import * as configs from '@/api/hooks/useGeneratorConfigs';
import * as generators from '@/api/hooks/useGenerators';
import { GeneratorDirsExtendedInfo } from '@/api/routes/generator-configs/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');
vi.mock('@/api/hooks/useGenerators');

const DATA: GeneratorDirsExtendedInfo = [
  {
    name: 'web',
    size_in_bytes: 213,
    last_modified: 1_767_225_600,
    generator_ids: ['web-live'],
  },
  {
    name: 'api',
    size_in_bytes: 512,
    last_modified: 1_767_312_000,
    generator_ids: [],
  },
  {
    name: 'metrics',
    size_in_bytes: null,
    last_modified: null,
    generator_ids: [],
  },
];

function setup(
  options: {
    data?: GeneratorDirsExtendedInfo;
    projectNameFilter?: string;
    instancesFilter?: string[];
    usageMode?: UsageMode;
  } = {}
) {
  const idle = { mutate: vi.fn(), isPending: false } as never;

  vi.mocked(configs.useDeleteGeneratorConfigMutation).mockReturnValue(idle);
  vi.mocked(configs.useRenameGeneratorConfigMutation).mockReturnValue(idle);
  vi.mocked(configs.useGeneratorDirs).mockReturnValue({
    data: options.data ?? DATA,
  } as never);
  vi.mocked(generators.useGenerators).mockReturnValue({
    data: [],
    isSuccess: true,
  } as never);

  renderWithProviders(
    <MemoryRouter>
      <GeneratorDirsTable
        data={options.data ?? DATA}
        projectNameFilter={options.projectNameFilter}
        instancesFilter={options.instancesFilter}
        usageMode={options.usageMode}
      />
    </MemoryRouter>
  );

  return { user: userEvent.setup() };
}

/** The project names the table is showing. */
function listed(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[0]?.textContent ?? '');
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The table lists the projects of the workspace and what uses each of
 * them, which is what the filters above it narrow. A project in use
 * cannot be deleted, so which instances point at it is part of the row
 * rather than something to find out afterwards.
 */
describe('GeneratorDirsTable', () => {
  it('lists every project, by name', () => {
    setup();

    // The table opens sorted by name, so the order is its own rather
    // than the order the workspace was read in.
    expect(listed()).toEqual(['api', 'metrics', 'web']);
  });

  it('names the instances that use a project', () => {
    setup();

    expect(screen.getByText('web-live')).toBeInTheDocument();
  });

  it('says a project nothing uses is not used', () => {
    setup({ data: [DATA[1]!] });

    expect(screen.getByText('Not used')).toBeInTheDocument();
  });

  it('narrows to the projects in use', () => {
    setup({ usageMode: 'used' });

    expect(listed()).toEqual(['web']);
  });

  it('narrows to the projects nothing uses', () => {
    setup({ usageMode: 'unused' });

    expect(listed()).toEqual(['api', 'metrics']);
  });

  it('narrows by the name of the project', () => {
    setup({ projectNameFilter: 'me' });

    expect(listed()).toEqual(['metrics']);
  });

  it('narrows by the instance that uses it', () => {
    setup({ instancesFilter: ['web-live'] });

    expect(listed()).toEqual(['web']);
  });

  it('says so when the filters leave nothing', () => {
    setup({ projectNameFilter: 'nothing-matches' });

    expect(listed()).toEqual([]);
  });

  it('reads a project whose size is unknown without failing', () => {
    setup({ data: [DATA[2]!] });

    expect(listed()).toEqual(['metrics']);
  });

  it('sorts by a column when its control is used', async () => {
    const { user } = setup();

    await user.click(
      screen.getByRole('button', { name: /Sort by project name/ })
    );

    expect(listed()).toEqual(['web', 'metrics', 'api']);
  });

  it('offers the actions of a project on its row', () => {
    setup();

    expect(
      screen.getAllByRole('button', { name: 'Project actions' })
    ).toHaveLength(3);
  });
});
