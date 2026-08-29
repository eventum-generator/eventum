import { ModalsProvider } from '@mantine/modals';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AboutModal } from './AboutModal';
import { useInstanceInfo } from '@/api/hooks/useInstance';
import { InstanceInfo } from '@/api/routes/instance/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useInstance');

const INFO = {
  app_version: '2.7.0',
  python_version: '3.14.3',
  python_implementation: 'CPython',
  python_compiler: 'GCC 11.4.0',
  python_free_threaded: true,
  python_gil_enabled: false,
  platform: 'Linux-6.18-x86_64',
  host_name: 'host',
  host_ip_v4: '127.0.0.1',
  boot_timestamp: 1_755_000_000,
  cpu_count: 8,
  cpu_frequency_mhz: 3000,
  cpu_percent: 12,
  memory_total_bytes: 1024,
  memory_used_bytes: 512,
  memory_available_bytes: 512,
  process_memory_bytes: 100,
  process_open_fds: 10,
  process_max_fds: 1024,
  network_sent_bytes: 0,
  network_received_bytes: 0,
  disk_written_bytes: 0,
  disk_read_bytes: 0,
  uptime: 100,
} as InstanceInfo;

function setup(
  info: InstanceInfo | null = INFO,
  state: Record<string, unknown> = {}
) {
  vi.mocked(useInstanceInfo).mockReturnValue({
    data: info ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...state,
  } as unknown as ReturnType<typeof useInstanceInfo>);

  renderWithProviders(
    <ModalsProvider>
      <AboutModal />
    </ModalsProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The plate is what a user copies into a bug report, so it has to name
 * the build precisely - and the free-threaded build with the GIL off is
 * exactly the detail a report is useless without.
 */
describe('AboutModal', () => {
  it('names the version of the instance', () => {
    setup();

    expect(screen.getByText('2.7.0')).toBeInTheDocument();
  });

  it('names the runtime it runs on', () => {
    setup();

    expect(screen.getByText('3.14.3')).toBeInTheDocument();
    expect(screen.getByText('CPython')).toBeInTheDocument();
    expect(screen.getByText('GCC 11.4.0')).toBeInTheDocument();
  });

  it('names the platform and when the host came up', () => {
    setup();

    expect(screen.getByText('Linux-6.18-x86_64')).toBeInTheDocument();
    expect(screen.getByText('Host')).toBeInTheDocument();
  });

  it('reports a free-threaded build with the lock released', () => {
    setup();

    expect(screen.getByText(/free.?threaded/i)).toBeInTheDocument();
  });

  it('reports a stock build differently', () => {
    setup({
      ...INFO,
      python_free_threaded: false,
      python_gil_enabled: true,
    } as InstanceInfo);

    expect(screen.queryByText(/free.?threaded/i)).not.toBeInTheDocument();
  });

  it('hands the whole plate over for a report', async () => {
    const user = userEvent.setup();
    const written: string[] = [];
    const writeText = vi.fn((text: string) => {
      written.push(text);

      return Promise.resolve();
    });

    // jsdom exposes the clipboard as a getter only.
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    setup();

    await user.click(screen.getByRole('button', { name: /Copy details/ }));

    expect(writeText).toHaveBeenCalledTimes(1);
    expect(written[0]).toContain('2.7.0');
  });

  it('waits while the instance is being read', () => {
    setup(null, { isLoading: true });

    expect(screen.queryByText('2.7.0')).not.toBeInTheDocument();
  });

  it('reports a failure to read it', () => {
    setup(null, {
      isLoading: false,
      isError: true,
      error: new Error('no connection'),
    });

    expect(screen.getByText(/no connection/)).toBeInTheDocument();
  });
});
