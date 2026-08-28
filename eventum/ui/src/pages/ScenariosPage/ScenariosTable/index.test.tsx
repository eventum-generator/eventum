import { RowSelectionState } from '@tanstack/react-table';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ScenarioStatusMode, ScenariosTable } from './index';
import { ScenarioRow } from './types';
import * as generators from '@/api/hooks/useGenerators';
import * as scenarios from '@/api/hooks/useScenarios';
import * as startup from '@/api/hooks/useStartup';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGenerators');
vi.mock('@/api/hooks/useScenarios');
vi.mock('@/api/hooks/useStartup');

function row(name: string, overrides: Partial<ScenarioRow> = {}): ScenarioRow {
  return {
    name,
    generatorIds: [`${name}-a`],
    generatorCount: 1,
    runningCount: 0,
    stoppedCount: 1,
    initializingCount: 0,
    stoppingCount: 0,
    ...overrides,
  };
}

const DATA: ScenarioRow[] = [
  row('nightly', { runningCount: 1, stoppedCount: 0 }),
  row('smoke'),
  row('weekly', { initializingCount: 1, stoppedCount: 0 }),
];

/** Mounts the table with the selection state its parent holds. */
function Host({
  data,
  nameFilter,
  statusMode,
}: Readonly<{
  data: ScenarioRow[];
  nameFilter?: string;
  statusMode?: ScenarioStatusMode;
}>) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  return (
    <ScenariosTable
      data={data}
      nameFilter={nameFilter}
      statusMode={statusMode}
      rowSelection={rowSelection}
      onRowSelectionChange={setRowSelection}
      getAffectedScenarios={() => []}
    />
  );
}

function mockHooks() {
  // A row names the instances of its scenario, which are read from the
  // live list, and its menu reaches for the mutations it offers.
  const idle = { mutate: vi.fn(), isPending: false } as never;

  vi.mocked(generators.useGenerators).mockReturnValue({
    data: [],
    isSuccess: true,
  } as never);
  vi.mocked(generators.useBulkStartGeneratorMutation).mockReturnValue(idle);
  vi.mocked(generators.useBulkStopGeneratorMutation).mockReturnValue(idle);
  vi.mocked(generators.useUpdateGeneratorStatus).mockReturnValue(idle);
  vi.mocked(scenarios.useDeleteScenarioMutation).mockReturnValue(idle);
  vi.mocked(scenarios.useRenameScenarioMutation).mockReturnValue(idle);
  vi.mocked(scenarios.useScenarios).mockReturnValue({
    data: {},
  } as never);
  vi.mocked(startup.useStartupGenerators).mockReturnValue({
    data: [],
    isSuccess: true,
  } as never);
}

function setup(
  options: {
    data?: ScenarioRow[];
    nameFilter?: string;
    statusMode?: ScenarioStatusMode;
  } = {}
) {
  mockHooks();

  renderWithProviders(
    <MemoryRouter>
      <Host
        data={options.data ?? DATA}
        nameFilter={options.nameFilter}
        statusMode={options.statusMode}
      />
    </MemoryRouter>
  );

  return { user: userEvent.setup() };
}

/** The names of the scenarios the table is showing. */
function listed(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map(
      (tableRow) => within(tableRow).getAllByRole('cell')[1]?.textContent ?? ''
    );
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The table is the list a bulk action reads its targets from, so what it
 * shows and what it has selected have to agree with the filters above
 * it: a scenario filtered out of view must not stay selected behind it.
 */
describe('ScenariosTable', () => {
  it('lists every scenario by name', () => {
    setup();

    expect(listed()).toEqual(['nightly', 'smoke', 'weekly']);
  });

  it('names the instances a scenario groups', () => {
    setup({
      data: [
        row('nightly', {
          generatorIds: ['web-live', 'api-live'],
          generatorCount: 2,
        }),
      ],
    });

    // The column lists them rather than counting them, so the row says
    // which instances a bulk action would reach.
    expect(screen.getByText('web-live')).toBeInTheDocument();
    expect(screen.getByText('api-live')).toBeInTheDocument();
  });

  it('narrows to the scenarios that are running', () => {
    setup({ statusMode: 'running' });

    // A scenario counts as running while any of its instances is live
    // or still on the move, so the one starting up is in.
    expect(listed()).toEqual(['nightly', 'weekly']);
  });

  it('narrows to the scenarios at rest', () => {
    setup({ statusMode: 'inactive' });

    expect(listed()).toEqual(['smoke']);
  });

  it('narrows by name', () => {
    setup({ nameFilter: 'night' });

    expect(listed()).toEqual(['nightly']);
  });

  it('says so when the filters leave nothing', () => {
    setup({ nameFilter: 'nothing-matches' });

    expect(listed()).toEqual([]);
    expect(screen.getByText(/No scenarios|nothing/i)).toBeInTheDocument();
  });

  it('selects a scenario for the actions above the table', async () => {
    const { user } = setup();

    const [first] = screen.getAllByRole('row').slice(1);
    await user.click(within(first!).getByRole('checkbox'));

    expect(within(first!).getByRole('checkbox')).toBeChecked();
  });

  it('selects every scenario at once', async () => {
    const { user } = setup();

    const header = screen.getAllByRole('row')[0]!;
    await user.click(within(header).getByRole('checkbox'));

    for (const tableRow of screen.getAllByRole('row').slice(1)) {
      expect(within(tableRow).getByRole('checkbox')).toBeChecked();
    }
  });

  it('sorts by a column when its control is used', async () => {
    const { user } = setup();

    await user.click(screen.getByRole('button', { name: /Sort by name/ }));

    expect(listed()).toEqual(['weekly', 'smoke', 'nightly']);
  });

  it('offers the actions of a scenario on its row', () => {
    setup();

    expect(
      screen.getAllByRole('button', { name: 'Scenario actions' })
    ).toHaveLength(3);
  });
});
