import { AxiosRequestConfig, AxiosResponse } from 'axios';
import { describe, expect, it } from 'vitest';

import { describeAPIError } from '@/api/errorReport';
import { APIError } from '@/api/errors';

function makeResponse(status: number, data: unknown): AxiosResponse {
  return {
    status,
    statusText: '',
    data,
    headers: {},
    config: {},
  } as unknown as AxiosResponse;
}

const REQUEST: AxiosRequestConfig = {
  baseURL: '/api',
  url: '/generator-configs/demo/name',
  method: 'patch',
};

function makeError(status: number, data: unknown, message: string): APIError {
  return new APIError({
    message,
    details: `Server respond with status code ${status}`,
    response: makeResponse(status, data),
    requestConfig: REQUEST,
  });
}

describe('describeAPIError', () => {
  it('reports the sentence the server sent instead of the status title', () => {
    const report = describeAPIError(
      makeError(
        409,
        { detail: 'Instances using the project must be stopped' },
        'Resource already exists'
      )
    );

    expect(report.reported).toBe('Instances using the project must be stopped');
    expect(report.details).toBeUndefined();
    expect(report.exchange).toEqual({
      method: 'PATCH',
      url: '/api/generator-configs/demo/name',
      status: 409,
      title: 'Resource already exists',
    });
  });

  it('reports a message carried with a context alongside it', () => {
    const report = describeAPIError(
      makeError(
        500,
        {
          detail: {
            message: 'Failed to initialize plugin',
            context: { plugin_name: 'cron', reason: 'invalid expression' },
          },
        },
        'Server error'
      )
    );

    expect(report.reported).toBe('Failed to initialize plugin');
    expect(report.context).toEqual({
      plugin_name: 'cron',
      reason: 'invalid expression',
    });
    expect(report.issues).toEqual([]);
  });

  it('lists a rejected payload field by field', () => {
    const report = describeAPIError(
      makeError(
        422,
        {
          detail: [
            {
              type: 'string_too_short',
              loc: ['body', 'name'],
              msg: 'String should have at least 1 character',
            },
            {
              type: 'missing',
              loc: ['body', 'path'],
              msg: 'Field required',
            },
          ],
        },
        'Invalid payload'
      )
    );

    expect(report.issues).toEqual([
      {
        path: 'body.name',
        message: 'String should have at least 1 character',
      },
      { path: 'body.path', message: 'Field required' },
    ]);
    expect(report.reported).toBe('Invalid payload');
    expect(report.exchange?.title).toBeUndefined();
  });

  it('parses a body that arrived as text', () => {
    const report = describeAPIError(
      makeError(404, '{"detail": "File does not exist"}', 'Resource not found')
    );

    expect(report.reported).toBe('File does not exist');
  });

  it('keeps a body it cannot recognize as a context', () => {
    const report = describeAPIError(
      makeError(500, { detail: { code: 17 } }, 'Server error')
    );

    expect(report.reported).toBe('Server error');
    expect(report.context).toEqual({ code: 17 });
  });

  it('falls back to the status title when the body carries no detail', () => {
    const report = describeAPIError(
      makeError(502, '<html>Bad Gateway</html>', 'Server error')
    );

    expect(report.reported).toBe('Server error');
    expect(report.context).toBeUndefined();
    expect(report.exchange?.title).toBeUndefined();
  });

  it('explains a request that never got a response', () => {
    const report = describeAPIError(
      new APIError({
        message: 'Request timed out',
        details: 'timeout of 60000ms exceeded',
        requestConfig: REQUEST,
      })
    );

    expect(report.reported).toBe('Request timed out');
    expect(report.details).toBe('timeout of 60000ms exceeded');
    expect(report.exchange).toEqual({
      method: 'PATCH',
      url: '/api/generator-configs/demo/name',
      status: undefined,
      title: undefined,
    });
  });

  it('leaves the path of a problem it cannot locate empty', () => {
    const report = describeAPIError(
      makeError(422, { detail: [{ msg: 'Field required' }] }, 'Invalid payload')
    );

    expect(report.issues).toEqual([{ path: '', message: 'Field required' }]);
  });

  it('lists the fields of a response that does not match its schema', () => {
    const report = describeAPIError(
      new APIError({
        message: 'Unexpected server response',
        details:
          'Server respond with body that does not match to defined schema',
        responseValidationErrors: [
          { path: 'items.0.status', message: 'Invalid option' },
        ],
      })
    );

    expect(report.reported).toBe('Unexpected server response');
    expect(report.issues).toEqual([
      { path: 'items.0.status', message: 'Invalid option' },
    ]);
  });
});
