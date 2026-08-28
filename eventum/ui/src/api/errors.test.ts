import { AxiosResponse } from 'axios';
import { describe, expect, it } from 'vitest';

import { APIError } from './errors';

function withStatus(status: number): APIError {
  return new APIError({
    message: 'Failed',
    response: { status } as AxiosResponse,
  });
}

/**
 * Every failed request reaches a component as an `APIError`, and the
 * component branches on these predicates: an auth error signs the user
 * out, a server error is reported as one, a validation error opens the
 * details. A predicate that answers wrongly sends the user down the
 * wrong path with no other signal.
 */
describe('APIError', () => {
  it('stays an Error, so a catch can narrow on it', () => {
    const error = new APIError({ message: 'Failed', details: 'why' });

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(APIError);
    expect(error.name).toBe('APIError');
    expect(error.message).toBe('Failed');
    expect(error.details).toBe('why');
  });

  it('reports an unauthorised response as an auth error', () => {
    expect(withStatus(401).isAuthError()).toBe(true);
    expect(withStatus(403).isAuthError()).toBe(false);
  });

  it.each([
    [500, true],
    [503, true],
    [499, false],
    [404, false],
  ])('reports status %i as a server error: %s', (status, expected) => {
    expect(withStatus(status).isServerError()).toBe(expected);
  });

  it.each([
    [400, true],
    [404, true],
    [499, true],
    [500, false],
    [399, false],
  ])('reports status %i as a client error: %s', (status, expected) => {
    expect(withStatus(status).isClientError()).toBe(expected);
  });

  it('answers none of the status predicates when no response arrived', () => {
    const error = new APIError({ message: 'Request failed' });

    expect(error.isAuthError()).toBe(false);
    expect(error.isServerError()).toBe(false);
    expect(error.isClientError()).toBe(false);
  });

  it('reports a validation error only when it carries the issues', () => {
    expect(
      new APIError({
        message: 'Unexpected server response',
        responseValidationErrors: [{ path: 'items.0', message: 'expected' }],
      }).isResponseValidationError()
    ).toBe(true);

    expect(withStatus(422).isResponseValidationError()).toBe(false);
  });

  it('keeps an empty list of issues as a validation error', () => {
    expect(
      new APIError({
        message: 'Unexpected server response',
        responseValidationErrors: [],
      }).isResponseValidationError()
    ).toBe(true);
  });
});
