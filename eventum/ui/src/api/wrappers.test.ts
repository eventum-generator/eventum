import { AxiosResponse } from 'axios';
import { describe, expect, it } from 'vitest';
import { z } from 'zod';

import { APIError } from '@/api/errors';
import { validateResponse } from '@/api/wrappers';

const Schema = z.object({
  items: z.array(z.object({ status: z.literal('ok') })),
});

function makeResponse(data: unknown): Promise<AxiosResponse> {
  return Promise.resolve({ data } as AxiosResponse);
}

describe('validateResponse', () => {
  it('returns the body once it matches the schema', async () => {
    await expect(
      validateResponse(Schema, makeResponse({ items: [{ status: 'ok' }] }))
    ).resolves.toEqual({ items: [{ status: 'ok' }] });
  });

  it('names every field a mismatching body fails on', async () => {
    const failure = await validateResponse(
      Schema,
      makeResponse({ items: [{ status: 'gone' }] })
    ).catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(APIError);
    expect((failure as APIError).responseValidationErrors).toEqual([
      {
        path: 'items.0.status',
        message: 'Invalid input: expected "ok"',
      },
    ]);
  });
});
