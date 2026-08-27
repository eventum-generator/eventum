import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SourceUsage } from './SourceUsage';
import { SourceUsageEntry } from './source-usage';
import { renderWithProviders } from '@/test/render';

function entry(overrides: Partial<SourceUsageEntry> = {}): SourceUsageEntry {
  return {
    path: 'templates/main.jinja',
    writes: ['session'],
    reads: [],
    warnings: [],
    ...overrides,
  };
}

function setup(entries: SourceUsageEntry[] = [entry()]) {
  const onHighlightEdge = vi.fn();
  const onHoverNode = vi.fn();

  renderWithProviders(
    <SourceUsage
      generatorId="web"
      entries={entries}
      onHighlightEdge={onHighlightEdge}
      onHoverNode={onHoverNode}
    />
  );

  return { onHighlightEdge, onHoverNode, user: userEvent.setup() };
}

/**
 * What a generator does with the shared state is read off its templates
 * and scripts rather than declared, so this lists it per file: the keys
 * each one writes and reads. Where the reading could not be complete -
 * a key computed at render time, an update() of a whole mapping - the
 * file says so, because a listing that looks exhaustive and is not is
 * worse than one that admits the gap.
 */
describe('SourceUsage', () => {
  it('lists the file the usage was read from', () => {
    setup([entry({ path: 'templates/main.jinja' })]);

    expect(screen.getByText(/main\.jinja/)).toBeInTheDocument();
  });

  it('names the keys a file writes and the keys it reads apart', () => {
    setup([entry({ writes: ['session'], reads: ['fleet'] })]);

    expect(screen.getByText('writes')).toBeInTheDocument();
    expect(screen.getByText('reads')).toBeInTheDocument();
    expect(screen.getByText('session')).toBeInTheDocument();
    expect(screen.getByText('fleet')).toBeInTheDocument();
  });

  it('says nothing about a direction the file does not use', () => {
    setup([entry({ writes: ['session'], reads: [] })]);

    expect(screen.getByText('writes')).toBeInTheDocument();
    expect(screen.queryByText('reads')).toBeNull();
  });

  it('lists a file whose reading may be incomplete, and why', () => {
    setup([
      entry({
        writes: [],
        reads: [],
        warnings: ['dynamic_key'],
      }),
    ]);

    // The file appears even with no key at all, so a flagged file is
    // never hidden, and the mark beside it carries the reason.
    expect(screen.getByText(/main\.jinja/)).toBeInTheDocument();
    expect(document.querySelector('svg')).not.toBeNull();
  });

  it('lights the flow of a key the pointer rests on', async () => {
    const { user, onHighlightEdge } = setup([
      entry({ writes: ['session'], reads: [] }),
    ]);

    await user.hover(screen.getByText('session'));

    expect(onHighlightEdge).toHaveBeenCalledWith('web', 'session', 'write');
  });

  it('keeps the instance lit once the pointer leaves a key', async () => {
    const { user, onHoverNode } = setup();

    await user.hover(screen.getByText('session'));
    await user.unhover(screen.getByText('session'));

    // The flow goes out but the instance stays lit, so scanning its
    // keys does not make the diagram flicker.
    expect(onHoverNode).toHaveBeenCalledWith('instance-web');
  });

  it('lists every file of the generator', () => {
    setup([
      entry({ path: 'templates/first.jinja' }),
      entry({ path: 'templates/second.jinja' }),
    ]);

    expect(screen.getByText(/first\.jinja/)).toBeInTheDocument();
    expect(screen.getByText(/second\.jinja/)).toBeInTheDocument();
  });

  it('draws nothing for a generator that touches no key', () => {
    const { container } = renderWithProviders(
      <SourceUsage generatorId="web" entries={[]} />
    );

    expect(within(container).queryByText('writes')).toBeNull();
  });
});
