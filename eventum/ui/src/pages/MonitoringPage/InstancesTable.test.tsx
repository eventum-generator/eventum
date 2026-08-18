import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { InstancesTable } from './InstancesTable';
import { InstanceUsageRow } from './history';
import { instanceColors } from './instanceColors';
import { renderWithProviders } from '@/test/render';

const ROW: InstanceUsageRow = {
  id: 'calm',
  cpuPercent: 2,
  waitPercent: 0,
  diskWriteBps: 0,
  netSentBps: 0,
  threads: 5,
  outputEps: 1,
  failEps: 0,
  queueSize: 0,
  queueMaxsize: 10,
  queueBytes: 0,
  queueMaxBytes: 134_217_728,
  queuePercent: 0,
};

const ROWS: InstanceUsageRow[] = [
  {
    ...ROW,
    id: 'busy',
    cpuPercent: 75,
    waitPercent: 25,
    diskWriteBps: 2 * 1024 * 1024,
    netSentBps: 1024 * 1024,
    threads: 8,
    outputEps: 300,
    failEps: 2,
    queueSize: 4,
    queueBytes: 96 * 1024 * 1024,
    queuePercent: 75,
  },
  ROW,
];

function render(rows: InstanceUsageRow[] = ROWS, onSelect = vi.fn()) {
  renderWithProviders(
    <InstancesTable
      rows={rows}
      colorOf={instanceColors(rows.map((row) => row.id))}
      selectedId={null}
      onSelect={onSelect}
    />
  );
  return onSelect;
}

function ids(): (string | null)[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => row.textContent);
}

describe('InstancesTable', () => {
  it('reports what each instance occupies, heaviest first', () => {
    render();

    expect(ids()[0]).toContain('busy');
    expect(ids()[1]).toContain('calm');

    expect(screen.getByText('75.0%')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
    expect(screen.getByText('300/s')).toBeInTheDocument();
    expect(screen.getByText('2.00/s')).toBeInTheDocument();
    expect(screen.getByText('2MB/s')).toBeInTheDocument();
    expect(screen.getByText('1MB/s')).toBeInTheDocument();
    expect(screen.getByText('96MB / 128MB')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('sorts by any column', async () => {
    const user = userEvent.setup();
    render();

    await user.click(screen.getByLabelText('Sort by Instance'));
    expect(ids()[0]).toContain('busy');

    await user.click(screen.getByLabelText('Sort by Instance'));
    expect(ids()[0]).toContain('calm');

    await user.click(screen.getByLabelText('Sort by Output'));
    expect(ids()[0]).toContain('busy');
  });

  it('hands the selected instance to its owner', async () => {
    const user = userEvent.setup();
    const onSelect = render();

    await user.click(screen.getByText('calm'));

    expect(onSelect).toHaveBeenCalledWith('calm');
  });
});
