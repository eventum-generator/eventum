import { describe, expect, it } from 'vitest';

import { AuthType, HTTPAuthConfigSchema } from './auth';
import { HTTPOutputPluginConfigSchema } from './configs/http';

/**
 * The schema is the mirror of the backend config: what Studio accepts
 * has to be what the API accepts, otherwise a form validates green and
 * the save comes back rejected with an error far from the field that
 * caused it.
 */
describe('HTTPAuthConfigSchema', () => {
  it('resolves the variant by its type', () => {
    const parsed = HTTPAuthConfigSchema.parse({
      type: AuthType.Bearer,
      token: 'abc',
    });

    expect(parsed).toEqual({ type: AuthType.Bearer, token: 'abc' });
  });

  it.each(['tok en', 'tok\nen', 'token\n', 'tokеn'])(
    'refuses the token %j, which no header can carry',
    (token) => {
      expect(
        HTTPAuthConfigSchema.safeParse({ type: AuthType.Bearer, token }).success
      ).toBe(false);
    }
  );

  it('requires a username for basic authentication', () => {
    expect(
      HTTPAuthConfigSchema.safeParse({ type: AuthType.Basic, password: 'p' })
        .success
    ).toBe(false);
  });

  it('takes the placeholder a parameter is substituted into', () => {
    expect(
      HTTPAuthConfigSchema.safeParse({
        type: AuthType.OAuth2ClientCredentials,
        token_url: '${params.token_url}',
        client_id: 'id',
        client_secret: '${secrets.client_secret}',
      }).success
    ).toBe(true);
  });
});

describe('HTTPOutputPluginConfigSchema', () => {
  it.each(['Authorization', 'authorization', 'AUTHORIZATION'])(
    'refuses the %s header beside an auth section',
    (header) => {
      const result = HTTPOutputPluginConfigSchema.safeParse({
        url: 'https://api.example.com/ingest',
        headers: { [header]: 'Bearer abc' },
        auth: { type: AuthType.Bearer, token: 'abc' },
      });

      expect(result.success).toBe(false);
      expect(result.error?.issues[0]?.path).toEqual(['headers']);
    }
  );

  it('keeps the header valid on its own', () => {
    expect(
      HTTPOutputPluginConfigSchema.safeParse({
        url: 'https://api.example.com/ingest',
        headers: { Authorization: 'Bearer abc' },
      }).success
    ).toBe(true);
  });

  it('refuses a header value that cannot be sent', () => {
    expect(
      HTTPOutputPluginConfigSchema.safeParse({
        url: 'https://api.example.com/ingest',
        headers: { 'X-Retry': 3 },
      }).success
    ).toBe(false);
  });
});
