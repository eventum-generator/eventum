import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InputPluginsNamedConfig } from '../generator-configs/schemas';
import { EventPluginNamedConfig } from '../generator-configs/schemas/plugins/event';
import { Format } from '../generator-configs/schemas/plugins/output/formatters';
import {
  clearTemplateEventPluginSharedState,
  deleteTemplateEventPluginGlobalStateKey,
  deleteTemplateEventPluginLocalStateKey,
  deleteTemplateEventPluginSharedStateKey,
  formatEvents,
  generateTimestamps,
  getTemplateEventPluginGlobalState,
  initializeEventPlugin,
  produceEvents,
  releaseEventPlugin,
  updateTemplateEventPluginSharedState,
} from './index';
import { apiClient } from '@/api/client';
import { APIError } from '@/api/errors';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const get = vi.mocked(apiClient.get);
const post = vi.mocked(apiClient.post);
const patch = vi.mocked(apiClient.patch);
const del = vi.mocked(apiClient.delete);

const INPUT_CONFIG: InputPluginsNamedConfig = [
  { timer: { seconds: 5, count: 1 } },
];

const TEMPLATE_CONFIG = {
  mode: 'all',
  templates: [{ main: { template: './templates/main.jinja' } }],
};

const EVENT_CONFIG = {
  template: TEMPLATE_CONFIG,
} as unknown as EventPluginNamedConfig;

beforeEach(() => {
  for (const mock of [get, post, patch, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

/**
 * The preview endpoints run the pipeline of a project that is only open
 * in the studio, so the configuration travels as the body while the
 * knobs travel as query parameters. Swapping the two silently previews
 * the saved configuration instead of the edited one.
 */
describe('generateTimestamps', () => {
  it('sends the input configuration as the body and the knobs as query', async () => {
    post.mockResolvedValue({
      data: {
        span_edges: ['2026-08-20T10:00:00'],
        span_counts: { timer: [3] },
        total: 3,
        first_timestamps: null,
        last_timestamps: null,
        timestamps: ['2026-08-20T10:00:00'],
      },
    });

    const result = await generateTimestamps(
      'web',
      10,
      true,
      'UTC',
      null,
      INPUT_CONFIG
    );

    expect(post).toHaveBeenCalledWith(
      '/preview/web/input-plugins/generate',
      INPUT_CONFIG,
      { params: { size: 10, skip_past: true, timezone: 'UTC', span: null } }
    );
    expect(result.total).toBe(3);
  });

  it('accepts a result that carries no timestamp list', async () => {
    post.mockResolvedValue({
      data: {
        span_edges: [],
        span_counts: {},
        total: 0,
        first_timestamps: null,
        last_timestamps: null,
        timestamps: null,
      },
    });

    await expect(
      generateTimestamps('web', 10, false, 'UTC', '5m', INPUT_CONFIG)
    ).resolves.toMatchObject({ total: 0 });
  });

  it('rejects a fractional count in a span', async () => {
    post.mockResolvedValue({
      data: {
        span_edges: [],
        span_counts: { timer: [1.5] },
        total: 1,
        first_timestamps: null,
        last_timestamps: null,
        timestamps: null,
      },
    });

    await expect(
      generateTimestamps('web', 10, false, 'UTC', null, INPUT_CONFIG)
    ).rejects.toBeInstanceOf(APIError);
  });
});

describe('the event plugin instance', () => {
  it('is created with the configuration currently in the studio', async () => {
    await initializeEventPlugin('web', EVENT_CONFIG);

    expect(post).toHaveBeenCalledWith('/preview/web/event-plugin', {
      template: TEMPLATE_CONFIG,
    });
  });

  it('is released by deleting it', async () => {
    await releaseEventPlugin('web');

    expect(del).toHaveBeenCalledWith('/preview/web/event-plugin');
  });

  it('produces events for the parameters it is given', async () => {
    post.mockResolvedValue({
      data: { events: ['{}'], errors: [], exhausted: false },
    });

    const result = await produceEvents('web', [
      { timestamp: '2026-08-20T10:00:00', tags: [] },
    ]);

    expect(post).toHaveBeenCalledWith('/preview/web/event-plugin/produce', [
      { timestamp: '2026-08-20T10:00:00', tags: [] },
    ]);
    expect(result.events).toEqual(['{}']);
  });

  it('reports a failure against the event it happened on', async () => {
    post.mockResolvedValue({
      data: {
        events: [],
        errors: [{ index: 0, message: 'boom', context: { reason: 'why' } }],
        exhausted: false,
      },
    });

    const result = await produceEvents('web', [
      { timestamp: '2026-08-20T10:00:00', tags: [] },
    ]);

    expect(result.errors[0]?.index).toBe(0);
    expect(result.errors[0]?.context.reason).toBe('why');
  });

  it('rejects a failure pointing before the first event', async () => {
    post.mockResolvedValue({
      data: {
        events: [],
        errors: [{ index: -1, message: 'boom', context: {} }],
        exhausted: false,
      },
    });

    await expect(
      produceEvents('web', [{ timestamp: '2026-08-20T10:00:00', tags: [] }])
    ).rejects.toBeInstanceOf(APIError);
  });
});

describe('template state', () => {
  it('reads the global state of the previewed plugin', async () => {
    get.mockResolvedValue({ data: { counter: 3 } });

    await expect(getTemplateEventPluginGlobalState('web')).resolves.toEqual({
      counter: 3,
    });
    expect(get).toHaveBeenCalledWith('/preview/web/event-plugin/state/global');
  });

  it('merges into the shared state with a patch, not a put', async () => {
    await updateTemplateEventPluginSharedState('web', { counter: 1 });

    expect(patch).toHaveBeenCalledWith(
      '/preview/web/event-plugin/template/state/shared',
      { counter: 1 }
    );
  });

  it('clears the shared state without naming a key', async () => {
    await clearTemplateEventPluginSharedState('web');

    expect(del).toHaveBeenCalledWith(
      '/preview/web/event-plugin/template/state/shared'
    );
  });

  it.each([
    [
      'shared',
      deleteTemplateEventPluginSharedStateKey,
      '/preview/web/event-plugin/template/state/shared/a%2Fb',
    ],
    [
      'global',
      deleteTemplateEventPluginGlobalStateKey,
      '/preview/web/event-plugin/state/global/a%2Fb',
    ],
  ])('escapes a key deleted from the %s state', async (_scope, remove, url) => {
    await remove('web', 'a/b');

    expect(del).toHaveBeenCalledWith(url);
  });

  it('escapes a key deleted from a local state, keeping the alias', async () => {
    await deleteTemplateEventPluginLocalStateKey('web', 'main', 'a/b');

    expect(del).toHaveBeenCalledWith(
      '/preview/web/event-plugin/template/state/local/main/a%2Fb'
    );
  });
});

describe('formatEvents', () => {
  it('reports how many of the given events the formatter accepted', async () => {
    post.mockResolvedValue({
      data: {
        events: ['{"a":1}'],
        formatted_count: 1,
        errors: [{ message: 'bad', original_event: 'oops' }],
      },
    });

    const result = await formatEvents('web', {
      formatter_config: { format: Format.JSON },
      events: ['{"a":1}', 'oops'],
    });

    expect(post).toHaveBeenCalledWith('/preview/web/formatter/format', {
      formatter_config: { format: Format.JSON },
      events: ['{"a":1}', 'oops'],
    });
    expect(result.formatted_count).toBe(1);
    expect(result.errors[0]?.original_event).toBe('oops');
  });
});
