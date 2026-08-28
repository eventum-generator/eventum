import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  addGeneratorToScenario,
  clearScenarioGlobalState,
  deleteScenario,
  deleteScenarioGlobalStateKey,
  getGlobalsUsage,
  getScenario,
  getScenarioGlobalState,
  listScenarios,
  removeGeneratorFromScenario,
  renameScenario,
  updateScenarioGlobalState,
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

beforeEach(() => {
  for (const mock of [get, post, patch, del]) {
    mock.mockReset();
    mock.mockResolvedValue({ data: undefined });
  }
});

/**
 * A scenario name is user-typed and reaches the URL as a path segment,
 * so a name with a space or a slash in it has to be escaped - otherwise
 * the request lands on a different scenario, or on no route at all.
 */
describe('scenarios', () => {
  it('lists the names the backend knows', async () => {
    get.mockResolvedValue({ data: ['corporate-network'] });

    await expect(listScenarios()).resolves.toEqual(['corporate-network']);
    expect(get).toHaveBeenCalledWith('/scenarios/');
  });

  it('reads one with the instances it groups', async () => {
    get.mockResolvedValue({
      data: { name: 'corporate network', generator_ids: ['web', 'db'] },
    });

    const scenario = await getScenario('corporate network');

    expect(get).toHaveBeenCalledWith('/scenarios/corporate%20network');
    expect(scenario.generator_ids).toEqual(['web', 'db']);
  });

  it('rejects a scenario without its instance list', async () => {
    get.mockResolvedValue({ data: { name: 'x' } });

    await expect(getScenario('x')).rejects.toBeInstanceOf(APIError);
  });

  it('deletes and renames by escaped name', async () => {
    await deleteScenario('corp net');
    await renameScenario('corp net', 'corp-net');

    expect(del).toHaveBeenCalledWith('/scenarios/corp%20net');
    expect(post).toHaveBeenCalledWith('/scenarios/corp%20net/rename', {
      new_name: 'corp-net',
    });
  });

  it('escapes both the scenario and the instance when grouping one', async () => {
    await addGeneratorToScenario('corp net', 'web 1');

    expect(post).toHaveBeenCalledWith(
      '/scenarios/corp%20net/generators/web%201'
    );
  });

  it('escapes both when removing an instance from a scenario', async () => {
    await removeGeneratorFromScenario('corp net', 'web 1');

    expect(del).toHaveBeenCalledWith(
      '/scenarios/corp%20net/generators/web%201'
    );
  });
});

describe('globals usage', () => {
  it('reports what a generator reads and writes, and what it cannot tell', async () => {
    get.mockResolvedValue({
      data: {
        writes: [{ key: 'counter', path: 'templates/main.jinja' }],
        reads: [],
        warnings: [{ type: 'dynamic_key', path: 'templates/main.jinja' }],
      },
    });

    const usage = await getGlobalsUsage('corp', 'web');

    expect(get).toHaveBeenCalledWith(
      '/scenarios/corp/generators/web/globals-usage'
    );
    expect(usage.writes[0]?.key).toBe('counter');
    expect(usage.warnings[0]?.type).toBe('dynamic_key');
  });

  it('rejects a warning of a kind the app cannot explain', async () => {
    get.mockResolvedValue({
      data: {
        writes: [],
        reads: [],
        warnings: [{ type: 'something_else', path: 'x' }],
      },
    });

    await expect(getGlobalsUsage('corp', 'web')).rejects.toBeInstanceOf(
      APIError
    );
  });
});

describe('the shared global state', () => {
  it('is read as an arbitrary map', async () => {
    get.mockResolvedValue({ data: { counter: 3, hosts: ['a'] } });

    await expect(getScenarioGlobalState('corp')).resolves.toEqual({
      counter: 3,
      hosts: ['a'],
    });
  });

  it('is merged with a patch, so untouched keys survive', async () => {
    await updateScenarioGlobalState('corp', { counter: 4 });

    expect(patch).toHaveBeenCalledWith('/scenarios/corp/globals', {
      counter: 4,
    });
  });

  it('is cleared without naming a key', async () => {
    await clearScenarioGlobalState('corp');

    expect(del).toHaveBeenCalledWith('/scenarios/corp/globals');
  });

  it('drops one key, escaped, without touching the rest', async () => {
    await deleteScenarioGlobalStateKey('corp', 'a/b');

    expect(del).toHaveBeenCalledWith('/scenarios/corp/globals/a%2Fb');
  });
});
