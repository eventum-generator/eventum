import { describe, expect, it } from 'vitest';

import {
  GenerationParametersSchema,
  LogParametersSchema,
  MCPParametersSchema,
  ServerParametersSchema,
  SettingsSchema,
} from './schemas';

const SETTINGS = {
  server: { host: '0.0.0.0', port: 9474 },
  generation: { timezone: 'UTC' },
  log: { level: 'info' },
  path: {
    logs: '/app/logs',
    startup: '/app/startup.yml',
    generators_dir: '/app/generators',
    keyring_cryptfile: '/app/cryptfile.cfg',
  },
};

/**
 * The settings form writes every field it holds, including the ones the
 * user cleared. An empty input therefore has to read back as "not set"
 * rather than as an empty string, which the backend would reject or -
 * worse - store as a host of "" that nothing binds to.
 */
describe('emptied fields', () => {
  it.each([
    ['an empty string', ''],
    ['null', null],
  ])('drops a host cleared to %s', (_label, value) => {
    const parsed = ServerParametersSchema.parse({ host: value });

    expect(parsed.host).toBeUndefined();
  });

  it('drops a cleared port instead of reading it as zero', () => {
    expect(ServerParametersSchema.parse({ port: '' }).port).toBeUndefined();
  });

  it('drops a cleared log level instead of failing the enum', () => {
    expect(LogParametersSchema.parse({ level: '' }).level).toBeUndefined();
  });

  // Batching by delay alone is asked for by a null size, so these two
  // keep the null the emptying step drops everywhere else - otherwise
  // the field reads back as unset and the backend applies its default
  // size instead of the condition the user picked.
  it('keeps a batch condition explicitly lifted with null', () => {
    const parsed = GenerationParametersSchema.parse({
      batch: { size: null, delay: 1 },
    });

    expect(parsed.batch?.size).toBeNull();
    expect(parsed.batch?.delay).toBe(1);
  });

  it.each([
    ['a size', 'size'],
    ['a delay', 'delay'],
  ])('still drops %s cleared to an empty input', (_label, field) => {
    const parsed = GenerationParametersSchema.parse({
      batch: { [field]: '' },
    });

    expect(parsed.batch?.[field as 'size' | 'delay']).toBeUndefined();
  });
});

describe('ServerParametersSchema', () => {
  it.each([0, 65_536, 1.5])('rejects %s as a port', (port) => {
    expect(ServerParametersSchema.safeParse({ port }).success).toBe(false);
  });

  it.each([1, 9474, 65_535])('accepts %i as a port', (port) => {
    expect(ServerParametersSchema.safeParse({ port }).success).toBe(true);
  });

  it('rejects an empty user, which would authenticate nobody', () => {
    // The value is emptied to undefined first, so an empty user reads
    // as unset rather than as a user named "".
    expect(
      ServerParametersSchema.parse({ auth: { user: '' } }).auth?.user
    ).toBeUndefined();
  });
});

describe('MCPParametersSchema', () => {
  it.each(['/mcp', '/'])('accepts the mount path %s', (path) => {
    expect(MCPParametersSchema.safeParse({ path }).success).toBe(true);
  });

  it.each(['mcp', 'http://host/mcp'])(
    'rejects the mount path %s for not starting at the root',
    (path) => {
      expect(MCPParametersSchema.safeParse({ path }).success).toBe(false);
    }
  );

  it('rejects a mount path with a trailing separator', () => {
    expect(MCPParametersSchema.safeParse({ path: '/mcp/' }).success).toBe(
      false
    );
  });
});

describe('GenerationParametersSchema', () => {
  it('rejects a timezone that is not a zone name', () => {
    expect(
      GenerationParametersSchema.safeParse({ timezone: 'Mars/Olympus' }).success
    ).toBe(false);
  });

  it.each([
    ['a batch of no events', { batch: { size: 0 } }],
    ['a delay below the floor', { batch: { delay: 0.01 } }],
    ['a queue holding no batches', { queue: { max_event_batches: 0 } }],
    ['no concurrency at all', { max_concurrency: 0 }],
    ['a write deadline of zero', { write_timeout: 0 }],
  ])('rejects %s', (_label, value) => {
    expect(GenerationParametersSchema.safeParse(value).success).toBe(false);
  });

  // The switch that lifts the byte limit writes a null, and an unset
  // field is the default limit rather than no limit - so the two must
  // stay apart on the way back as well.
  it('keeps an unlimited event queue asked for with null', () => {
    expect(
      GenerationParametersSchema.parse({ queue: { max_event_bytes: null } })
        .queue?.max_event_bytes
    ).toBeNull();
  });

  it('reads an omitted byte limit as unset rather than as no limit', () => {
    expect(
      GenerationParametersSchema.parse({ queue: {} }).queue?.max_event_bytes
    ).toBeUndefined();
  });
});

describe('LogParametersSchema', () => {
  it.each(['debug', 'info', 'warning', 'error', 'critical'])(
    'accepts the %s level',
    (level) => {
      expect(LogParametersSchema.safeParse({ level }).success).toBe(true);
    }
  );

  it('rejects a level it has no name for', () => {
    expect(LogParametersSchema.safeParse({ level: 'trace' }).success).toBe(
      false
    );
  });

  it('rejects a rotation size below a kilobyte', () => {
    expect(LogParametersSchema.safeParse({ max_bytes: 1023 }).success).toBe(
      false
    );
  });
});

describe('SettingsSchema', () => {
  it('accepts the settings tree the backend serves', () => {
    expect(SettingsSchema.safeParse(SETTINGS).success).toBe(true);
  });

  it.each(['server', 'generation', 'log', 'path'])(
    'requires the %s section',
    (section) => {
      const settings: Record<string, unknown> = { ...SETTINGS };
      delete settings[section];

      expect(SettingsSchema.safeParse(settings).success).toBe(false);
    }
  );

  it.each(['logs', 'startup', 'generators_dir', 'keyring_cryptfile'])(
    'requires the %s path, which has no default',
    (key) => {
      const path: Record<string, unknown> = { ...SETTINGS.path };
      delete path[key];

      expect(SettingsSchema.safeParse({ ...SETTINGS, path }).success).toBe(
        false
      );
    }
  );
});
