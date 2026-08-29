import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StateStrip } from './StateStrip';
import { CurrentMetrics, InstanceUsageRow } from './history';
import { FlowAgg } from './metrics';
import { renderWithProviders } from '@/test/render';

const FLOW: FlowAgg = {
  generated: 1200,
  produced: 1150,
  written: 1100,
  dropped: 50,
  produceFailed: 0,
  writeFailed: 0,
  formatFailed: 0,
};

const CURRENT: CurrentMetrics = {
  inputEps: 12,
  producedEps: 11,
  outputEps: 10,
  failEps: 0,
  failing: false,
  diskReadBps: 0,
  diskWriteBps: 0,
  netRecvBps: 0,
  netSentBps: 0,
};

function usageRow(queuePercent: number, id = 'web'): InstanceUsageRow {
  return {
    id,
    cpuPercent: 0,
    waitPercent: 0,
    diskWriteBps: 0,
    netSentBps: 0,
    threads: 1,
    outputEps: 0,
    failEps: 0,
    queueSize: 0,
    queueMaxsize: 10,
    queueBytes: 0,
    queueMaxBytes: null,
    queuePercent,
  };
}

function setup(
  overrides: Partial<{
    flow: FlowAgg;
    current: CurrentMetrics;
    rows: InstanceUsageRow[];
    instances: number;
  }> = {}
) {
  renderWithProviders(
    <StateStrip
      flow={FLOW}
      current={CURRENT}
      rows={[usageRow(0)]}
      instances={2}
      {...overrides}
    />
  );
}

/** The figure of one reading, by the name of the reading. */
function reading(label: string): HTMLElement {
  const found = document.querySelector(`[data-reading="${label}"]`);

  if (found === null) {
    throw new Error(`the strip drew no ${label} reading`);
  }

  return found as HTMLElement;
}

/**
 * The strip is the one line an operator reads to know whether the fleet
 * is healthy. Two of its figures are derived rather than reported: the
 * fullest queue across every instance, and whether anything is failing
 * at all - and both are what turn the line from a readout into a
 * warning.
 */
describe('StateStrip', () => {
  it('counts the running instances', () => {
    setup({ instances: 3 });

    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('instances')).toBeInTheDocument();
  });

  it('names a single instance in the singular', () => {
    setup({ instances: 1 });

    expect(screen.getByText('instance')).toBeInTheDocument();
  });

  it('reports the rate of every stage', () => {
    setup();

    expect(reading('input')).toHaveTextContent(/^12(\.\d+)?\/s$/);
    expect(reading('event')).toHaveTextContent(/^11(\.\d+)?\/s$/);
    expect(reading('output')).toHaveTextContent(/^10(\.\d+)?\/s$/);
  });

  it('reports the totals of the whole run', () => {
    setup();

    // Each total is drawn as one line - "1.1K written" - so the label
    // is not a text node of its own.
    for (const label of ['generated', 'produced', 'written', 'dropped']) {
      expect(screen.getByText(new RegExp(`${label}$`))).toBeInTheDocument();
    }
  });

  it('takes the fullest queue across every instance', () => {
    setup({ rows: [usageRow(10, 'a'), usageRow(84, 'b'), usageRow(30, 'c')] });

    expect(reading('fullest queue')).toHaveTextContent('84%');
  });

  it('reads no instances as an empty queue rather than as unknown', () => {
    setup({ rows: [] });

    expect(reading('fullest queue')).toHaveTextContent('0%');
  });

  it('leaves the failure figure uncoloured while nothing fails', () => {
    setup();

    const failing = reading('failing');

    expect(failing).toHaveTextContent(/^0(\.\d+)?\/s$/);
    expect(failing.getAttribute('style') ?? '').not.toContain('red');
  });

  it('colours the failure figure once something fails', () => {
    setup({ current: { ...CURRENT, failEps: 4, failing: true } });

    const failing = reading('failing');

    expect(failing).toHaveTextContent(/^4(\.\d+)?\/s$/);
    expect(failing.getAttribute('style') ?? '').toContain('red');
  });

  it('leaves a queue below the warning level uncoloured', () => {
    setup({ rows: [usageRow(20)] });

    expect(reading('fullest queue').getAttribute('style') ?? '').not.toMatch(
      /yellow|red/
    );
  });

  it('colours a queue that is close to its limit', () => {
    setup({ rows: [usageRow(95)] });

    expect(reading('fullest queue').getAttribute('style') ?? '').toMatch(
      /yellow|red/
    );
  });
});
