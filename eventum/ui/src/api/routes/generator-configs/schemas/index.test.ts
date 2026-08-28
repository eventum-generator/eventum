import { describe, expect, it } from 'vitest';

import {
  FileNodesListSchema,
  GeneratorConfigSchema,
  GeneratorDirsExtendedInfoSchema,
} from './index';

const VALID_CONFIG = {
  input: [{ timer: { seconds: 5, count: 1 } }],
  event: {
    template: {
      mode: 'all',
      templates: [{ main: { template: './templates/main.jinja' } }],
    },
  },
  output: [{ file: { path: './output/output.log' } }],
};

/**
 * The shape the studio sends back when a project is saved. Every stage
 * is required and each holds a named plugin config, so a config that
 * parses here is one the backend can load.
 */
describe('GeneratorConfigSchema', () => {
  it('accepts a config with all three stages', () => {
    expect(GeneratorConfigSchema.safeParse(VALID_CONFIG).success).toBe(true);
  });

  it.each(['input', 'event', 'output'])('requires the %s stage', (stage) => {
    const config: Record<string, unknown> = { ...VALID_CONFIG };
    delete config[stage];

    expect(GeneratorConfigSchema.safeParse(config).success).toBe(false);
  });

  it.each(['input', 'output'])(
    'rejects an empty list of %s plugins',
    (stage) => {
      expect(
        GeneratorConfigSchema.safeParse({ ...VALID_CONFIG, [stage]: [] })
          .success
      ).toBe(false);
    }
  );

  it('rejects a plugin no stage knows', () => {
    expect(
      GeneratorConfigSchema.safeParse({
        ...VALID_CONFIG,
        input: [{ telepathy: { seconds: 1 } }],
      }).success
    ).toBe(false);
  });
});

describe('GeneratorDirsExtendedInfoSchema', () => {
  it('accepts a directory whose size and modification time are unknown', () => {
    expect(
      GeneratorDirsExtendedInfoSchema.safeParse([
        {
          name: 'project',
          size_in_bytes: null,
          last_modified: null,
          generator_ids: [],
        },
      ]).success
    ).toBe(true);
  });

  it('rejects a fractional size', () => {
    expect(
      GeneratorDirsExtendedInfoSchema.safeParse([
        {
          name: 'project',
          size_in_bytes: 1.5,
          last_modified: null,
          generator_ids: [],
        },
      ]).success
    ).toBe(false);
  });
});

describe('FileNodesListSchema', () => {
  it('accepts a tree nested more than one level deep', () => {
    expect(
      FileNodesListSchema.safeParse([
        {
          name: 'templates',
          is_dir: true,
          size_in_bytes: null,
          children: [
            {
              name: 'macros',
              is_dir: true,
              size_in_bytes: null,
              children: [
                {
                  name: 'base.jinja',
                  is_dir: false,
                  size_in_bytes: 12,
                  children: null,
                },
              ],
            },
          ],
        },
      ]).success
    ).toBe(true);
  });

  it('accepts a file that carries no children key at all', () => {
    expect(
      FileNodesListSchema.safeParse([
        { name: 'generator.yml', is_dir: false, size_in_bytes: 40 },
      ]).success
    ).toBe(true);
  });

  it('rejects a node without a kind', () => {
    expect(
      FileNodesListSchema.safeParse([
        { name: 'generator.yml', size_in_bytes: 40, children: null },
      ]).success
    ).toBe(false);
  });
});
