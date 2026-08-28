import { ModalsProvider } from '@mantine/modals';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SettingsPage from './index';
import {
  useInstanceSettings,
  useRestartInstanceMutation,
  useUpdateInstanceSettingsMutation,
} from '@/api/hooks/useInstance';
import { Settings } from '@/api/routes/instance/schemas';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useInstance');

const SETTINGS = {
  server: {
    host: '0.0.0.0',
    port: 9474,
    ui: { enabled: true },
    api: { enabled: true },
    auth: { user: 'eventum', password: 'eventum' },
    ssl: { enabled: false },
    mcp: { enabled: false, allow_write: false, path: '/mcp' },
  },
  generation: {
    timezone: 'UTC',
    batch: { size: 10_000, delay: 1 },
    queue: { max_timestamp_batches: 10, max_event_batches: 10 },
    keep_order: false,
    max_concurrency: 100,
    write_timeout: 10,
  },
  log: {
    level: 'info',
    third_party_level: 'warning',
    format: 'plain',
    max_bytes: 10_485_760,
    backups: 5,
  },
  path: {
    logs: '/app/logs',
    startup: '/app/startup.yml',
    generators_dir: '/app/generators',
    keyring_cryptfile: '/app/cryptfile.cfg',
  },
} as unknown as Settings;

const update = {
  mutate: vi.fn((_variables: unknown, handlers?: { onSuccess?: () => void }) =>
    handlers?.onSuccess?.()
  ),
  isPending: false,
};
const restart = { mutate: vi.fn(), isPending: false };

function settingsQuery(overrides: Record<string, unknown> = {}) {
  return {
    data: SETTINGS,
    isLoading: false,
    isSuccess: true,
    isError: false,
    error: null,
    ...overrides,
  } as ReturnType<typeof useInstanceSettings>;
}

function setup(query = settingsQuery()) {
  vi.mocked(useInstanceSettings).mockReturnValue(query);

  renderWithProviders(
    <ModalsProvider>
      <SettingsPage />
    </ModalsProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  update.mutate.mockImplementation(
    (_variables: unknown, handlers?: { onSuccess?: () => void }) =>
      handlers?.onSuccess?.()
  );
  globalThis.location.hash = '';
  vi.mocked(useUpdateInstanceSettingsMutation).mockReturnValue(
    update as unknown as ReturnType<typeof useUpdateInstanceSettingsMutation>
  );
  vi.mocked(useRestartInstanceMutation).mockReturnValue(
    restart as unknown as ReturnType<typeof useRestartInstanceMutation>
  );
});

/**
 * The settings page edits the file the instance boots from, so saving
 * restarts it. That makes two things load-bearing: the values shown are
 * the stored ones rather than the schema defaults, and a save is never
 * one click away.
 */
describe('SettingsPage', () => {
  it('opens on the server section', () => {
    setup();

    expect(screen.getByDisplayValue('0.0.0.0')).toBeInTheDocument();
    expect(screen.getByDisplayValue('9474')).toBeInTheDocument();
  });

  it('shows every section in the sidebar', () => {
    setup();

    for (const label of ['Server', 'Generation', 'Paths', 'Logging']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it('shows the stored generation defaults once that section is opened', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getAllByText('Generation')[0]!);

    expect(screen.getByDisplayValue('10000')).toBeInTheDocument();
  });

  it('shows the paths the instance reads from', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getAllByText('Paths')[0]!);

    expect(screen.getByDisplayValue('/app/logs')).toBeInTheDocument();
    expect(screen.getByDisplayValue('/app/generators')).toBeInTheDocument();
  });

  it('shows the logging settings', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getAllByText('Logging')[0]!);

    expect(screen.getAllByDisplayValue('info').length).toBeGreaterThan(0);
  });

  it('records the open section in the address, so a reload returns to it', async () => {
    const user = userEvent.setup();
    const replaceState = vi.spyOn(globalThis.history, 'replaceState');
    setup();

    await user.click(screen.getAllByText('Paths')[0]!);

    expect(replaceState).toHaveBeenCalledWith(null, '', '#path');

    replaceState.mockRestore();
  });

  it('opens on the section the address names', () => {
    globalThis.location.hash = '#log';
    setup();

    expect(screen.getAllByDisplayValue('info').length).toBeGreaterThan(0);
  });

  it('falls back to the server section for an address it does not know', () => {
    globalThis.location.hash = '#nowhere';
    setup();

    expect(screen.getByDisplayValue('0.0.0.0')).toBeInTheDocument();
  });

  it('waits while the settings are being read', () => {
    setup(
      settingsQuery({ data: undefined, isLoading: true, isSuccess: false })
    );

    expect(screen.queryByText('Server')).not.toBeInTheDocument();
  });

  it('reports a failure to read them', () => {
    setup(
      settingsQuery({
        data: undefined,
        isLoading: false,
        isSuccess: false,
        isError: true,
        error: new Error('no connection'),
      })
    );

    expect(
      screen.getByText('Failed to get instance settings')
    ).toBeInTheDocument();
    expect(screen.getByText(/no connection/)).toBeInTheDocument();
  });

  /**
   * A save takes the instance down for a moment, so it is confirmed
   * first - and only then are the settings written and the restart
   * asked for.
   */
  it('confirms before saving, then saves and restarts', async () => {
    const user = userEvent.setup();
    setup();

    await user.clear(screen.getByDisplayValue('0.0.0.0'));
    await user.type(
      screen.getByRole('textbox', { name: /Bind host/ }),
      '127.0.0.1'
    );
    await user.click(screen.getByRole('button', { name: /Save/ }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Restart' }));

    expect(update.mutate).toHaveBeenCalledTimes(1);

    const sent = update.mutate.mock.calls[0]?.[0] as { settings: Settings };
    expect(sent.settings.server.host).toBe('127.0.0.1');

    // The instance reads its settings at startup, so a save that does
    // not restart it leaves it serving the old ones.
    expect(restart.mutate).toHaveBeenCalledTimes(1);
  });

  it('writes nothing when the confirmation is dismissed', async () => {
    const user = userEvent.setup();
    setup();

    await user.clear(screen.getByDisplayValue('0.0.0.0'));
    await user.type(
      screen.getByRole('textbox', { name: /Bind host/ }),
      '127.0.0.1'
    );
    await user.click(screen.getByRole('button', { name: /Save/ }));

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(update.mutate).not.toHaveBeenCalled();
  });
});
