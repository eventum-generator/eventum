import { describe, expect, it } from 'vitest';

import {
  HANDLE_Y,
  PipelineNodeData,
  buildEdges,
  buildNodes,
  computeGraphHeight,
  structureKey,
  updateNodesData,
} from './layoutNodes';
import { GeneratorStats } from '@/api/routes/generators/schemas';

function stats(
  overrides: {
    inputs?: number;
    outputs?: number;
    produced?: number;
    produceFailed?: number;
    written?: number;
    writeFailed?: number;
    formatFailed?: number;
    generated?: number;
  } = {}
): GeneratorStats {
  const {
    inputs = 1,
    outputs = 1,
    produced = 10,
    produceFailed = 0,
    written = 10,
    writeFailed = 0,
    formatFailed = 0,
    generated = 10,
  } = overrides;

  return {
    id: 'web',
    start_time: '2026-01-01T00:00:00+00:00',
    resources: {} as never,
    input: Array.from({ length: inputs }, (_, i) => ({
      plugin_name: 'timer',
      plugin_id: i + 1,
      generated,
    })),
    event: {
      plugin_name: 'template',
      plugin_id: 10,
      produced,
      produce_failed: produceFailed,
      dropped: 0,
    },
    output: Array.from({ length: outputs }, (_, i) => ({
      plugin_name: 'file',
      plugin_id: 20 + i,
      written,
      write_failed: writeFailed,
      format_failed: formatFailed,
    })),
    total_generated: generated,
    total_written: written,
    uptime: 1,
    input_eps: 1,
    output_eps: 1,
  } as GeneratorStats;
}

/** The reading a node carries, by its name. */
function metric(node: { data: PipelineNodeData }, label: string) {
  return node.data.metrics.find((m) => m.label === label);
}

/**
 * The graph draws the pipeline of one instance: its input plugins, the
 * event plugin they feed, and the output plugins that take what it
 * produces. Its shape is computed rather than laid out by the library,
 * so the columns have to stay lined up on the handles the edges leave
 * from - and the readings have to keep following the stats without the
 * graph being rebuilt, which is what keeps the view from resetting on
 * every poll.
 */
describe('buildNodes', () => {
  it('draws a node per plugin of the pipeline', () => {
    const nodes = buildNodes(stats({ inputs: 2, outputs: 3 }));

    expect(nodes.map((node) => node.id)).toEqual([
      'input-1',
      'input-2',
      'event-0',
      'output-20',
      'output-21',
      'output-22',
    ]);
  });

  it('puts the three stages in three columns', () => {
    const nodes = buildNodes(stats());
    const x = (id: string) => nodes.find((n) => n.id === id)?.position.x;

    expect(x('input-1')).toBeLessThan(x('event-0')!);
    expect(x('event-0')).toBeLessThan(x('output-20')!);
  });

  it('centres a column on the handles the edges leave from', () => {
    const nodes = buildNodes(stats({ inputs: 3, outputs: 1 }));
    const anchors = nodes
      .filter((node) => node.id.startsWith('input-'))
      .map((node) => node.position.y + HANDLE_Y);
    const event = nodes.find((node) => node.id === 'event-0')!;

    // The single event node sits level with the middle of the three
    // inputs, so the edges meet it head-on rather than at an angle.
    expect(event.position.y + HANDLE_Y).toBe(anchors[1]);
  });

  it('carries the count of what each stage did', () => {
    const nodes = buildNodes(stats({ generated: 7, produced: 5, written: 3 }));

    expect(metric(nodes[0]!, 'Generated')?.value).toBe(7);
    expect(metric(nodes[1]!, 'Produced')?.value).toBe(5);
    expect(metric(nodes[2]!, 'Written')?.value).toBe(3);
  });

  it('marks a failure as one and a count of none as not', () => {
    const clean = buildNodes(stats());
    const failing = buildNodes(stats({ produceFailed: 2, writeFailed: 1 }));

    expect(metric(clean[1]!, 'Produce failed')?.isError).toBe(false);
    expect(metric(failing[1]!, 'Produce failed')?.isError).toBe(true);
    expect(metric(failing[2]!, 'Write failed')?.isError).toBe(true);
  });
});

describe('buildEdges', () => {
  it('runs every input into the event plugin and out to every output', () => {
    const edges = buildEdges(stats({ inputs: 2, outputs: 2 }));

    expect(edges.map((edge) => edge.id)).toEqual([
      'edge-input-1-event',
      'edge-input-2-event',
      'edge-event-output-20',
      'edge-event-output-21',
    ]);
  });

  it('runs the pipeline one way', () => {
    const edges = buildEdges(stats());

    expect(edges[0]).toMatchObject({ source: 'input-1', target: 'event-0' });
    expect(edges[1]).toMatchObject({ source: 'event-0', target: 'output-20' });
  });
});

describe('structureKey', () => {
  it('stays the same while only the counters move', () => {
    expect(structureKey(stats({ produced: 1 }))).toBe(
      structureKey(stats({ produced: 9999 }))
    );
  });

  it.each([
    ['an input plugin is added', { inputs: 2 }],
    ['an output plugin is added', { outputs: 2 }],
  ])('changes when %s', (_label, overrides) => {
    expect(structureKey(stats(overrides))).not.toBe(structureKey(stats()));
  });
});

describe('updateNodesData', () => {
  it('moves the readings without moving the nodes', () => {
    const nodes = buildNodes(stats({ inputs: 2, generated: 1 }));
    const updated = updateNodesData(nodes, stats({ inputs: 2, generated: 8 }));

    expect(metric(updated[0]!, 'Generated')?.value).toBe(8);
    expect(updated.map((node) => node.position)).toEqual(
      nodes.map((node) => node.position)
    );
  });

  it('leaves a node whose plugin is gone as it was', () => {
    const nodes = buildNodes(stats({ inputs: 2, generated: 4 }));
    const updated = updateNodesData(nodes, stats({ inputs: 1, generated: 9 }));

    // A rebuild is what removes a node; until then the one left behind
    // keeps what it last read rather than showing another plugin's.
    expect(metric(updated[1]!, 'Generated')?.value).toBe(4);
  });
});

describe('computeGraphHeight', () => {
  it('holds a floor a small pipeline does not draw below', () => {
    expect(computeGraphHeight(stats())).toBe(180);
  });

  it('grows with the longest column', () => {
    expect(computeGraphHeight(stats({ inputs: 4 }))).toBe(480);
    expect(computeGraphHeight(stats({ outputs: 4 }))).toBe(480);
  });
});
