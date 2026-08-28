import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FormatterTab } from './index';
import { useFormatEventsMutation } from '@/api/hooks/usePreview';
import { FormattingResult } from '@/api/routes/preview/schemas';
import { ProjectNameProvider } from '@/pages/ProjectPage/context/ProjectNameContext';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/hooks/usePreview');

let format: {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
};

function result(
  events: string[],
  errors: { message: string; original_event: string | null }[] = []
): FormattingResult {
  return {
    events,
    formatted_count: events.length,
    errors,
  } as FormattingResult;
}

function setup(formatted = result(['{"a":1}'])) {
  format = {
    mutate: vi.fn(
      (
        _variables: unknown,
        handlers?: { onSuccess?: (data: FormattingResult) => void }
      ) => handlers?.onSuccess?.(formatted)
    ),
    isPending: false,
  };

  vi.mocked(useFormatEventsMutation).mockReturnValue(
    format as unknown as ReturnType<typeof useFormatEventsMutation>
  );

  renderWithProviders(
    <ProjectNameProvider initialProjectName="web">
      <FormatterTab />
    </ProjectNameProvider>
  );
}

function eventFields(): HTMLElement[] {
  return screen.getAllByPlaceholderText('raw event ...');
}

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * The tool feeds sample events through the formatter the output plugin
 * is configured with, so what it sends is the events currently typed
 * and the configuration currently picked. An event list that cannot be
 * grown or emptied would make the tool useless for a batch formatter,
 * which behaves differently for one event than for several.
 */
describe('FormatterTab', () => {
  it('opens on one empty event', () => {
    setup();

    expect(eventFields()).toHaveLength(1);
    expect(eventFields()[0]).toHaveValue('');
  });

  it('takes more events on request', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: 'Add event' }));

    expect(eventFields()).toHaveLength(2);
  });

  it('drops one event without touching the others', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(eventFields()[0]!, 'first');
    await user.click(screen.getByRole('button', { name: 'Add event' }));
    await user.type(eventFields()[1]!, 'second');

    await user.click(screen.getAllByTitle('Delete event')[0]!);

    expect(eventFields()).toHaveLength(1);
    expect(eventFields()[0]).toHaveValue('second');
  });

  it('sends the events as typed, under the project', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(eventFields()[0]!, 'raw');
    await user.click(screen.getByRole('button', { name: /Format/ }));

    const sent = format.mutate.mock.calls[0]?.[0] as {
      name: string;
      body: { events: string[] };
    };

    expect(sent.name).toBe('web');
    expect(sent.body.events).toEqual(['raw']);
  });

  it('sends the formatter it was configured with', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: /Format/ }));

    const sent = format.mutate.mock.calls[0]?.[0] as {
      body: { formatter_config: { format: string } };
    };

    expect(sent.body.formatter_config.format).toBe('plain');
  });

  it('shows what the formatter produced', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole('button', { name: /Format/ }));

    expect(await screen.findByText(/\{"a":1\}/)).toBeInTheDocument();
  });

  it('reports an event the formatter refused', async () => {
    const user = userEvent.setup();
    setup(result([], [{ message: 'bad shape', original_event: 'oops' }]));

    await user.click(screen.getByRole('button', { name: /Format/ }));

    expect(await screen.findByText(/bad shape/)).toBeInTheDocument();
  });

  it('offers no formatting once every event is gone', async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByTitle('Delete event'));

    expect(screen.getByRole('button', { name: /Format/ })).toBeDisabled();
  });
});
