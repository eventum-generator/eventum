import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LogsPanel } from './LogsPanel';
import { streamInstanceLogs } from '@/api/routes/instance';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/routes/instance', () => ({
  streamInstanceLogs: vi.fn(() => ({ close: vi.fn() })),
}));

const streamMock = vi.mocked(streamInstanceLogs);

afterEach(() => {
  streamMock.mockClear();
});

describe('LogsPanel', () => {
  it('streams the main channel on open', () => {
    renderWithProviders(<LogsPanel />);

    expect(streamMock.mock.calls.map(([channel]) => channel)).toEqual(['main']);
  });

  it('streams the channel the reader selects', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LogsPanel />);

    await user.click(screen.getByText('Access'));

    expect(streamMock.mock.calls.map(([channel]) => channel)).toEqual([
      'main',
      'server_access',
    ]);
  });
});
