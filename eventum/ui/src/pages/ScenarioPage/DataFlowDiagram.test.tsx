import { fireEvent, screen } from '@testing-library/react';
import { type Edge } from '@xyflow/react';
import { describe, expect, it, vi } from 'vitest';

import { DataFlowDiagram } from './DataFlowDiagram';
import { EdgeContext, buildEdges, computeDiagramHeight } from './data-flow';
import { GeneratorStatus } from '@/api/routes/generators/schemas';
import { renderWithProviders } from '@/test/render';

const IDLE: GeneratorStatus = {
  is_initializing: false,
  is_running: false,
  is_ended_up: false,
  is_ended_up_successfully: false,
  is_stopping: false,
};

const RUNNING: GeneratorStatus = { ...IDLE, is_running: true };

interface Usage {
  writes: { key: string }[];
  reads: { key: string }[];
}

interface Options {
  entries?: { id: string; path: string }[];
  statuses?: [string, GeneratorStatus][];
  usage?: [string, Usage | undefined][];
  highlightedNodeId?: string | null;
  onInstanceClick?: (id: string) => void;
}

function setup(options: Options = {}) {
  const entries = options.entries ?? [
    { id: 'writer', path: 'writer/generator.yml' },
    { id: 'reader', path: 'reader/generator.yml' },
  ];

  const usage: [string, Usage | undefined][] = options.usage ?? [
    ['writer', { writes: [{ key: 'session' }], reads: [] }],
    ['reader', { writes: [], reads: [{ key: 'session' }] }],
  ];

  return renderWithProviders(
    <DataFlowDiagram
      scenarioEntries={entries}
      generatorStatusMap={new Map(options.statuses ?? [])}
      globalsUsageMap={new Map(usage)}
      highlightedNodeId={options.highlightedNodeId}
      onInstanceClick={options.onInstanceClick}
    />
  );
}

/** The nodes the diagram drew, by kind. */
function nodes(kind: 'instance' | 'key'): NodeListOf<Element> {
  return document.querySelectorAll(`.react-flow__node-${kind}`);
}

/** The dots that carry the state of each instance. */
function glowingDots(): Element[] {
  return [...document.querySelectorAll('.ev-status-dot')].filter(
    (dot) => (dot as HTMLElement).dataset.glow === 'true'
  );
}

/**
 * The diagram is the only place a scenario shows how its instances reach
 * each other: through the keys of the shared state, one writing what
 * another reads. That is read off the templates rather than declared, so
 * an instance that shares nothing must draw no flow, and a key several
 * instances write is still one key.
 */
describe('DataFlowDiagram', () => {
  it('draws a node per instance of the scenario', () => {
    setup();

    expect(nodes('instance')).toHaveLength(2);
    expect(screen.getByText('writer')).toBeInTheDocument();
    expect(screen.getByText('reader')).toBeInTheDocument();
  });

  it('draws a node per key the instances share', () => {
    setup();

    expect(nodes('key')).toHaveLength(1);
    expect(screen.getByText('session')).toBeInTheDocument();
  });

  it('draws one key node however many instances share it', () => {
    setup({
      entries: [
        { id: 'a', path: 'a/generator.yml' },
        { id: 'b', path: 'b/generator.yml' },
      ],
      usage: [
        ['a', { writes: [{ key: 'session' }], reads: [] }],
        ['b', { writes: [{ key: 'session' }], reads: [] }],
      ],
    });

    expect(nodes('key')).toHaveLength(1);
  });

  it('draws the instances of a scenario that shares nothing', () => {
    setup({
      usage: [
        ['writer', undefined],
        ['reader', undefined],
      ],
    });

    expect(nodes('instance')).toHaveLength(2);
    expect(nodes('key')).toHaveLength(0);
  });

  it('marks a running instance apart from one at rest', () => {
    setup({
      statuses: [
        ['writer', RUNNING],
        ['reader', IDLE],
      ],
    });

    // The state of an instance is carried by the dot beside its name,
    // and only a live one is lit.
    expect(document.querySelectorAll('.ev-status-dot')).toHaveLength(2);
    expect(glowingDots()).toHaveLength(1);
  });

  it('draws an instance with no status of its own as one at rest', () => {
    setup({ statuses: [] });

    // A generator the manager does not know is not running, and the
    // diagram has to draw it as such rather than leave it unmarked.
    expect(glowingDots()).toHaveLength(0);
  });

  it('opens the instance a node stands for', () => {
    const onInstanceClick = vi.fn();

    setup({ onInstanceClick });

    // The click alone is dispatched: a press on the canvas also begins a
    // pan, and the library that pans it measures the surface it is
    // dragged over - which jsdom does not lay out.
    fireEvent.click(screen.getByText('writer'));

    expect(onInstanceClick).toHaveBeenCalledWith('writer');
  });
});

const NO_HIGHLIGHT: EdgeContext = {
  highlightedNodeId: null,
  highlightedEdgeId: null,
  hasHighlight: false,
};

/**
 * A flow is drawn from the measured positions of the two nodes it joins,
 * which jsdom does not measure - so what the flows are is read off the
 * model the diagram is built from.
 */
describe('the flows of a scenario', () => {
  it('runs a write from the instance to the key', () => {
    const [edge] = buildEdges(
      new Map([['writer', { writes: [{ key: 'session' }], reads: [] }]]),
      NO_HIGHLIGHT
    );

    expect(edge).toMatchObject({
      source: 'instance-writer',
      target: 'key-session',
    });
  });

  it('runs a read from the key to the instance', () => {
    const [edge] = buildEdges(
      new Map([['reader', { writes: [], reads: [{ key: 'session' }] }]]),
      NO_HIGHLIGHT
    );

    expect(edge).toMatchObject({
      source: 'key-session',
      target: 'instance-reader',
    });
  });

  it('runs a flow per access, in both directions', () => {
    const edges = buildEdges(
      new Map([
        ['writer', { writes: [{ key: 'session' }], reads: [] }],
        ['reader', { writes: [], reads: [{ key: 'session' }] }],
      ]),
      NO_HIGHLIGHT
    );

    expect(edges).toHaveLength(2);
  });

  it('runs no flow for an instance that touches nothing', () => {
    expect(
      buildEdges(new Map([['idle', undefined]]), NO_HIGHLIGHT)
    ).toHaveLength(0);
  });

  it('runs one flow for a key an instance reads twice', () => {
    // A template can read the same key in several places, and that is
    // one flow rather than one per line.
    expect(
      buildEdges(
        new Map([
          [
            'reader',
            { writes: [], reads: [{ key: 'session' }, { key: 'session' }] },
          ],
        ]),
        NO_HIGHLIGHT
      )
    ).toHaveLength(1);
  });

  it('animates every flow while nothing is picked out', () => {
    const edges = buildEdges(
      new Map([
        ['writer', { writes: [{ key: 'session' }], reads: [] }],
        ['other', { writes: [{ key: 'other' }], reads: [] }],
      ]),
      NO_HIGHLIGHT
    );

    expect(edges.every((edge: Edge) => edge.animated)).toBe(true);
  });

  it('leaves only the flows of a picked instance lit', () => {
    const edges = buildEdges(
      new Map([
        ['writer', { writes: [{ key: 'session' }], reads: [] }],
        ['other', { writes: [{ key: 'other' }], reads: [] }],
      ]),
      {
        highlightedNodeId: 'instance-writer',
        highlightedEdgeId: null,
        hasHighlight: true,
      }
    );

    const lit = edges.filter((edge: Edge) => edge.animated);

    expect(lit).toHaveLength(1);
    expect(lit[0]?.source).toBe('instance-writer');
  });

  it('lights the flow that is picked out itself', () => {
    const edges = buildEdges(
      new Map([['writer', { writes: [{ key: 'session' }], reads: [] }]]),
      {
        highlightedNodeId: null,
        highlightedEdgeId: 'write-writer-session',
        hasHighlight: true,
      }
    );

    expect(edges[0]?.animated).toBe(true);
  });
});

describe('the height of the diagram', () => {
  it('holds a floor no scenario draws below', () => {
    expect(computeDiagramHeight(0, 0)).toBe(220);
    expect(computeDiagramHeight(1, 1)).toBe(220);
  });

  it('grows with whichever column is longer', () => {
    // The instances and the keys sit in two columns, so the taller of
    // the two is what the diagram has to fit.
    expect(computeDiagramHeight(5, 2)).toBe(560);
    expect(computeDiagramHeight(2, 5)).toBe(560);
  });
});
