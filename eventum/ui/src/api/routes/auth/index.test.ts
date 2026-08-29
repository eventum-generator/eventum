import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getCurrentUser, login, logout } from './index';
import { apiClient } from '@/api/client';
import { APIError } from '@/api/errors';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const get = vi.mocked(apiClient.get);
const post = vi.mocked(apiClient.post);

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

/**
 * The credentials travel as Basic auth on the login request and the
 * session then lives in a cookie. Sending them anywhere else - as a
 * body, or on the wrong path - fails as a plain 401 that reads like
 * wrong credentials.
 */
describe('login', () => {
  it('sends the credentials as basic auth and returns the username', async () => {
    post.mockResolvedValue({ data: 'eventum' });

    await expect(login('eventum', 'secret')).resolves.toBe('eventum');

    expect(post).toHaveBeenCalledWith('/auth/login', null, {
      auth: { username: 'eventum', password: 'secret' },
    });
  });

  it('fails when the body is not a username', async () => {
    post.mockResolvedValue({ data: { user: 'eventum' } });

    await expect(login('eventum', 'secret')).rejects.toThrow();
  });
});

describe('getCurrentUser', () => {
  it('returns the username the session belongs to', async () => {
    get.mockResolvedValue({ data: 'eventum' });

    await expect(getCurrentUser()).resolves.toBe('eventum');
    expect(get).toHaveBeenCalledWith('/auth/me');
  });

  it('reports a body of the wrong shape as a validation error', async () => {
    get.mockResolvedValue({ data: 42 });

    const failure = await getCurrentUser().catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(APIError);
    expect((failure as APIError).isResponseValidationError()).toBe(true);
  });
});

describe('logout', () => {
  it('drops the session without expecting a body back', async () => {
    post.mockResolvedValue({ data: undefined });

    await expect(logout()).resolves.toBeUndefined();
    expect(post).toHaveBeenCalledWith('/auth/logout');
  });
});
