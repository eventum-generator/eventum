import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { VersatileDatetimeToolModal } from './VersatileDatetimeToolModal';
import { APIError } from '@/api/errors';
import { useNormalizedVersatileDatetimeMutation } from '@/api/hooks/usePreview';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/usePreview');

interface Handlers {
  onSuccess?: (value: string) => void;
  onError?: (error: unknown) => void;
}

/**
 * The tool asks the backend what an expression resolves to, so the
 * answer is what the mutation is made to give back.
 */
function setup(answer: { value?: string; error?: unknown } = {}) {
  const mutate = vi.fn(
    (
      _args: { name: string; parameters: unknown },
      handlers: Handlers = {}
    ): void => {
      if (answer.error === undefined) {
        handlers.onSuccess?.(answer.value ?? '2026-01-01T00:00:00+00:00');
      } else {
        handlers.onError?.(answer.error);
      }
    }
  );

  vi.mocked(useNormalizedVersatileDatetimeMutation).mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof useNormalizedVersatileDatetimeMutation>);

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <VersatileDatetimeToolModal />
    </ProjectNameProvider>
  );

  return mutate;
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The tool exists because the versatile datetime format accepts things
 * no field can validate on its own - "in 2 days", "+1h", "Monday" - and
 * only the backend knows what any of them resolve to. So what matters is
 * that the expression reaches it with the parameters beside it, and that
 * both answers it can give are shown as such.
 */
describe('VersatileDatetimeToolModal', () => {
  it('sends the expression with the parameters it is read under', async () => {
    const user = userEvent.setup();
    const mutate = setup();

    await user.click(screen.getByRole('textbox', { name: 'Value' }));
    await user.paste('3 months ago');
    await user.click(screen.getByRole('button', { name: 'Normalize' }));

    expect(mutate).toHaveBeenCalledWith(
      {
        name: 'web',
        parameters: expect.objectContaining({
          value: '3 months ago',
          timezone: 'UTC',
          none_point: 'now',
        }),
      },
      expect.anything()
    );
  });

  it('shows what the expression resolves to', async () => {
    const user = userEvent.setup();
    setup({ value: '2026-03-01T12:00:00+00:00' });

    await user.click(screen.getByRole('textbox', { name: 'Value' }));
    await user.paste('now');
    await user.click(screen.getByRole('button', { name: 'Normalize' }));

    await waitFor(() => expect(screen.getByText('Valid')).toBeInTheDocument());
    expect(screen.getByText('2026-03-01T12:00:00+00:00')).toBeInTheDocument();
  });

  it('reports an expression the backend refuses as invalid', async () => {
    const user = userEvent.setup();
    setup({
      error: new APIError({
        message: 'Invalid payload',
        response: { status: 422 } as never,
      }),
    });

    await user.click(screen.getByRole('textbox', { name: 'Value' }));
    await user.paste('nonsense');
    await user.click(screen.getByRole('button', { name: 'Normalize' }));

    await waitFor(() =>
      expect(screen.getByText('Expression is invalid')).toBeInTheDocument()
    );

    // The two answers are exclusive - a refused expression must not be
    // reported as one that resolved.
    expect(screen.queryByText('Valid')).toBeNull();
  });

  it('does not call a failure of the request an invalid expression', async () => {
    const user = userEvent.setup();
    setup({
      error: new APIError({
        message: 'Server error',
        response: { status: 500 } as never,
      }),
    });

    await user.click(screen.getByRole('textbox', { name: 'Value' }));
    await user.paste('now');
    await user.click(screen.getByRole('button', { name: 'Normalize' }));

    expect(screen.queryByText('Expression is invalid')).toBeNull();
    expect(screen.queryByText('Valid')).toBeNull();
  });

  it('sends an empty value as no value at all', async () => {
    const user = userEvent.setup();
    const mutate = setup();

    // An empty field is not an expression, and the backend takes the
    // absence of one as the point the plugin would default to.
    await user.click(screen.getByRole('button', { name: 'Normalize' }));

    expect(mutate).toHaveBeenCalledWith(
      { name: 'web', parameters: expect.objectContaining({ value: null }) },
      expect.anything()
    );
  });

  it('carries the point an absent value is read as', async () => {
    const user = userEvent.setup();
    const mutate = setup();

    await user.click(screen.getByRole('radio', { name: 'Max' }));
    await user.click(screen.getByRole('button', { name: 'Normalize' }));

    expect(mutate).toHaveBeenCalledWith(
      {
        name: 'web',
        parameters: expect.objectContaining({ none_point: 'max' }),
      },
      expect.anything()
    );
  });

  it('names the formats the field accepts', () => {
    setup();

    // The list is the whole point of the modal for a user who does not
    // know the format yet.
    expect(screen.getByText('+1d12h30m15s')).toBeInTheDocument();
    expect(screen.getByText('2 weeks ago')).toBeInTheDocument();
    expect(screen.getByText('never')).toBeInTheDocument();
  });
});
