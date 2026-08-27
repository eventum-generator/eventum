import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import YAML from 'yaml';

import { TimePatternParams } from './index';
import * as configs from '@/api/hooks/useGeneratorConfigs';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/useGeneratorConfigs');

const PATTERN = YAML.stringify({
  label: 'business hours',
  oscillator: { period: 1, unit: 'hours', start: 'now', end: 'never' },
  multiplier: { ratio: 100 },
  randomizer: { deviation: 0.3, direction: 'mixed', sampling: 1024 },
  spreader: { distribution: 'beta', parameters: { a: 15, b: 15 } },
});

type Handlers = { onSuccess?: () => void; onError?: (e: unknown) => void };

interface Options {
  content?: string;
  isLoading?: boolean;
  isError?: boolean;
  failSave?: boolean;
}

function setup(options: Options = {}) {
  const mutate = vi.fn((_args: unknown, handlers: Handlers = {}): void => {
    if (options.failSave === true) {
      handlers.onError?.(new Error('read only'));
    } else {
      handlers.onSuccess?.();
    }
  });

  vi.mocked(configs.useGeneratorFileContent).mockReturnValue({
    data: options.content ?? PATTERN,
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
    isSuccess: options.isLoading !== true && options.isError !== true,
    error: options.isError === true ? new Error('no file') : null,
  } as unknown as ReturnType<typeof configs.useGeneratorFileContent>);
  vi.mocked(configs.usePutGeneratorFileMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as never);

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <TimePatternParams filePath="patterns/business.yml" />
    </ProjectNameProvider>
  );

  return { mutate, user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * A time pattern lives in a file of its own, so this reads it, hands it
 * to the form and writes it back. A file that is not a pattern must be
 * reported rather than drawn as an empty form - the form would then save
 * a pattern over whatever the file actually held.
 */
describe('TimePatternParams', () => {
  it('opens the form on the pattern the file holds', async () => {
    setup();

    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: /Label/ })).toHaveValue(
        'business hours'
      )
    );
  });

  it('waits rather than drawing a form over nothing', () => {
    setup({ isLoading: true });

    expect(screen.queryByRole('textbox', { name: /Label/ })).toBeNull();
  });

  it('reports a file it could not read', () => {
    setup({ isError: true });

    expect(screen.getByText('Failed to load file')).toBeInTheDocument();
  });

  it('reports a file that is not a pattern', () => {
    setup({ content: YAML.stringify({ something: 'else' }) });

    expect(screen.getByText('Cannot display')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /Label/ })).toBeNull();
  });

  it('reports a file that is not even YAML', () => {
    setup({ content: 'label: [unclosed' });

    expect(screen.getByText('Cannot display')).toBeInTheDocument();
  });

  it('offers no save until the pattern is edited', () => {
    setup();

    expect(screen.getByRole('button', { name: 'Save file' })).toBeDisabled();
  });

  it('writes the edited pattern back as YAML', async () => {
    const { user, mutate } = setup();

    const label = screen.getByRole('textbox', { name: /Label/ });
    await user.click(label);
    await user.paste(' extended');
    await user.click(screen.getByRole('button', { name: 'Save file' }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'web',
        filepath: 'patterns/business.yml',
      }),
      expect.anything()
    );

    const written = (
      mutate.mock.calls[0]?.[0] as unknown as { content: string }
    ).content;
    expect(YAML.parse(written).label).toContain('extended');
  });

  it('keeps the save on offer when writing failed', async () => {
    const { user } = setup({ failSave: true });

    const label = screen.getByRole('textbox', { name: /Label/ });
    await user.click(label);
    await user.paste(' extended');
    await user.click(screen.getByRole('button', { name: 'Save file' }));

    // The edit is still unsaved, so it must remain savable.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Save file' })).toBeEnabled()
    );
  });
});
