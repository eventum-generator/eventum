import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ResourceTiles } from './ResourceTiles';
import { CurrentMetrics, ResourcePoint } from './history';
import { InstanceInfo } from '@/api/routes/instance/schemas';
import { renderWithProviders } from '@/test/render';

const MB = 1024 * 1024;

const INFO = {
  app_version: '2.7.0',
  python_version: '3.14.3',
  python_implementation: 'CPython',
  python_compiler: 'GCC',
  python_free_threaded: true,
  python_gil_enabled: false,
  platform: 'Linux',
  host_name: 'host',
  host_ip_v4: '127.0.0.1',
  boot_timestamp: 1_755_000_000,
  cpu_count: 8,
  cpu_frequency_mhz: 2999.7,
  cpu_percent: 12,
  memory_total_bytes: 100 * MB,
  memory_used_bytes: 40 * MB,
  memory_available_bytes: 60 * MB,
  process_memory_bytes: 10 * MB,
  process_open_fds: 20,
  process_max_fds: 1024,
  network_sent_bytes: 0,
  network_received_bytes: 0,
  disk_written_bytes: 0,
  disk_read_bytes: 0,
  uptime: 100,
} as InstanceInfo;

const CURRENT: CurrentMetrics = {
  inputEps: 0,
  producedEps: 0,
  outputEps: 0,
  failEps: 0,
  failing: false,
  diskReadBps: 1024,
  diskWriteBps: 2048,
  netRecvBps: 512,
  netSentBps: 256,
};

const RESOURCES: ResourcePoint[] = [
  {
    t: 0,
    cpu: 10,
    memPct: 40,
    appMem: 10,
    diskRead: 0,
    diskWrite: 0,
    netRecv: 0,
    netSent: 0,
  },
  {
    t: 5000,
    cpu: 20,
    memPct: 45,
    appMem: 12,
    diskRead: 100,
    diskWrite: 200,
    netRecv: 50,
    netSent: 25,
  },
];

function setup(overrides: Partial<InstanceInfo> = {}) {
  renderWithProviders(
    <ResourceTiles
      info={{ ...INFO, ...overrides } as InstanceInfo}
      resources={RESOURCES}
      current={CURRENT}
      points={30}
    />
  );
}

/** The tile a label belongs to, as markup. */
function tileHtml(label: string): string {
  return (
    screen.getByText(label).closest('.mantine-Paper-root')?.outerHTML ?? ''
  );
}

/**
 * The tiles report the host and the process side by side, and each
 * figure is derived rather than reported: the memory percentage from
 * two byte counters, the rates from cumulative ones. A tile that shows
 * nothing when a figure is missing reads as a healthy zero.
 */
describe('ResourceTiles', () => {
  it('draws a tile per resource', () => {
    setup();

    for (const label of ['CPU', 'Memory', 'Disk I/O', 'Network']) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it('reports the processor load the host reported', () => {
    setup({ cpu_percent: 37.4 });

    // Anchored: a substring check would also hold for 137%.
    expect(tileHtml('CPU')).toMatch(/>37%</);
  });

  it('derives the memory percentage from the byte counters', () => {
    setup();

    expect(tileHtml('Memory')).toMatch(/>40%</);
  });

  it('reads a host reporting no memory at all as none used', () => {
    setup({ memory_total_bytes: 0, memory_used_bytes: 0 });

    expect(tileHtml('Memory')).toMatch(/>0%</);
  });

  it('names how many cores the host has', () => {
    setup();

    expect(tileHtml('CPU')).toContain('8 cores');
  });

  it('marks an unknown core count rather than showing none', () => {
    setup({ cpu_count: null });

    expect(tileHtml('CPU')).toContain('? cores');
  });

  it('rounds the clock speed', () => {
    setup();

    expect(tileHtml('CPU')).toContain('3000 MHz');
  });

  // The rates are what the tile exists to report, and the two
  // directions are not interchangeable - a tile reporting the read rate
  // as the write rate looks entirely healthy.
  it('reports the disk rates, each in its own direction', () => {
    setup();

    const disk = tileHtml('Disk I/O');

    expect(disk).toMatch(/>1KB\/s</);
    expect(disk).toMatch(/>2KB\/s</);
  });

  it('reports the network rates, each in its own direction', () => {
    setup();

    const network = tileHtml('Network');

    expect(network).toMatch(/>512B\/s</);
    expect(network).toMatch(/>256B\/s</);
  });

  it('reads a rate of nothing as zero rather than as unknown', () => {
    renderWithProviders(
      <ResourceTiles
        info={INFO}
        resources={RESOURCES}
        current={{ ...CURRENT, diskReadBps: 0, diskWriteBps: 0 }}
        points={30}
      />
    );

    expect(tileHtml('Disk I/O')).toMatch(/>0B\/s</);
  });

  it('says which figures are the host and which the process', () => {
    setup();

    expect(tileHtml('CPU')).toMatch(/>host</);
    expect(tileHtml('Disk I/O')).toMatch(/>app</);
  });

  it('colours a processor load past the warning level', () => {
    setup({ cpu_percent: 95 });

    expect(tileHtml('CPU')).toMatch(/red|yellow/);
  });

  it('leaves a quiet processor uncoloured', () => {
    setup({ cpu_percent: 5 });

    expect(tileHtml('CPU')).toContain('green');
  });

  it('colours memory close to full', () => {
    setup({ memory_used_bytes: 95 * MB });

    expect(tileHtml('Memory')).toMatch(/red|yellow/);
  });
});
