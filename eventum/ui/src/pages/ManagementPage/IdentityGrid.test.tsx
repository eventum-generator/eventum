import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { IdentityGrid } from './IdentityGrid';
import { InstanceInfo } from '@/api/routes/instance/schemas';
import { renderWithProviders } from '@/test/render';

const INFO: InstanceInfo = {
  app_version: '2.7.0',
  python_version: '3.14.3',
  python_implementation: 'CPython',
  python_compiler: 'Clang 21.1.4',
  python_free_threaded: true,
  python_gil_enabled: false,
  platform: 'Linux-6.18-x86_64',
  host_name: 'eventum-host',
  // eslint-disable-next-line sonarjs/no-hardcoded-ip -- fixture value
  host_ip_v4: '10.0.0.2',
  boot_timestamp: 1_770_000_000,
  cpu_count: 8,
  cpu_frequency_mhz: 2400,
  cpu_percent: 12,
  memory_total_bytes: 16_000_000_000,
  memory_used_bytes: 4_000_000_000,
  memory_available_bytes: 12_000_000_000,
  network_sent_bytes: 0,
  network_received_bytes: 0,
  disk_written_bytes: 0,
  disk_read_bytes: 0,
  uptime: 3600,
};

function renderGrid(info: InstanceInfo): HTMLElement {
  const { container } = renderWithProviders(
    <MemoryRouter>
      <IdentityGrid info={info} />
    </MemoryRouter>
  );

  return container;
}

const alertGlyph = (container: HTMLElement) =>
  container.querySelector('.tabler-icon-alert-triangle');

describe('IdentityGrid', () => {
  it('shows the GIL off on a free-threaded build without an alert', () => {
    const container = renderGrid(INFO);

    expect(screen.getByText('GIL')).toBeInTheDocument();
    expect(screen.getByText('Disabled')).toBeInTheDocument();
    expect(alertGlyph(container)).toBeNull();
  });

  it('alerts when the GIL came back on a free-threaded build', () => {
    const container = renderGrid({ ...INFO, python_gil_enabled: true });

    expect(screen.getByText('Enabled')).toBeInTheDocument();
    expect(alertGlyph(container)).not.toBeNull();
  });

  it('shows the GIL on a standard build without an alert', () => {
    const container = renderGrid({
      ...INFO,
      python_free_threaded: false,
      python_gil_enabled: true,
    });

    expect(screen.getByText('Enabled')).toBeInTheDocument();
    expect(alertGlyph(container)).toBeNull();
  });
});
