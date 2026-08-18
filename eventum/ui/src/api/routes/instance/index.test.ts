import { afterEach, describe, expect, it, vi } from 'vitest';

import { streamInstanceLogs } from '@/api/routes/instance';

class SocketStub {
  static readonly urls: string[] = [];

  constructor(url: string) {
    SocketStub.urls.push(url);
  }
}

afterEach(() => {
  SocketStub.urls.length = 0;
  vi.unstubAllGlobals();
});

describe('streamInstanceLogs', () => {
  it('streams the requested channel', () => {
    vi.stubGlobal('WebSocket', SocketStub);

    streamInstanceLogs('server_access', 8192);

    expect(SocketStub.urls).toHaveLength(1);
    expect(SocketStub.urls[0]).toContain(
      '/api/instance/logs/server_access?end_offset=8192'
    );
  });
});
