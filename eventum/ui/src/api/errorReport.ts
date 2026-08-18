import { AxiosRequestConfig } from 'axios';

import { APIError, ValidationIssue } from '@/api/errors';

/** Protocol line of a failed exchange - what was called and how the
 * server answered, if it answered at all. */
export interface ReportedExchange {
  method?: string;
  /** Full target of the call, base URL included. */
  url?: string;
  status?: number;
  /** Title the status code is generalized to, carried only when the
   * server reported a message of its own. */
  title?: string;
}

/** Failure ranked by diagnostic value: what was reported first, the
 * protocol envelope last. */
export interface APIErrorReport {
  /** Sentence the server reported, or the client-side title when no
   * response arrived. */
  reported: string;
  /** Client-side explanation, carried only when no response arrived -
   * with one it just restates the status code. */
  details?: string;
  /** Structured context shipped alongside the reported sentence. */
  context?: unknown;
  /** Field-level problems: a rejected request payload or a response
   * that does not match its schema. */
  issues: ValidationIssue[];
  exchange?: ReportedExchange;
}

interface ReportedDetail {
  reported?: string;
  context?: unknown;
  issues: ValidationIssue[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// A response body arrives parsed unless the request asked for text, in
// which case axios hands the payload over as it came.
function parseBody(data: unknown): unknown {
  if (typeof data !== 'string') {
    return data;
  }

  try {
    return JSON.parse(data);
  } catch {
    return data;
  }
}

// A rejected request payload is reported per field, each entry naming
// the location it was found at.
function describeRejectedPayload(entries: unknown[]): ReportedDetail {
  const issues = entries
    .filter((entry) => isRecord(entry))
    .flatMap((entry) =>
      typeof entry.msg === 'string'
        ? [
            {
              path: Array.isArray(entry.loc) ? entry.loc.join('.') : '',
              message: entry.msg,
            },
          ]
        : []
    );

  return issues.length > 0 ? { issues } : { context: entries, issues: [] };
}

// The URL a request was sent to is split in two by the client.
function describeTarget(config: AxiosRequestConfig): string | undefined {
  const target = `${config.baseURL ?? ''}${config.url ?? ''}`;

  return target === '' ? undefined : target;
}

function describeDetail(detail: unknown): ReportedDetail {
  if (typeof detail === 'string') {
    return { reported: detail, issues: [] };
  }

  if (Array.isArray(detail)) {
    return describeRejectedPayload(detail);
  }

  if (isRecord(detail)) {
    return typeof detail.message === 'string'
      ? { reported: detail.message, context: detail.context, issues: [] }
      : { context: detail, issues: [] };
  }

  return { issues: [] };
}

/**
 * Rank an API error by diagnostic value.
 *
 * The message the server reported is the one that explains the failure;
 * the title and the details the client derives from the status code
 * only restate the code, and the request and response envelopes explain
 * nothing on their own.
 */
export function describeAPIError(error: APIError): APIErrorReport {
  const requestConfig = error.requestConfig;
  const response = error.response;
  const body = response === undefined ? undefined : parseBody(response.data);
  const detail = describeDetail(isRecord(body) ? body.detail : undefined);

  return {
    reported: detail.reported ?? error.message,
    details: response === undefined ? error.details : undefined,
    context: detail.context,
    issues: [...detail.issues, ...(error.responseValidationErrors ?? [])],
    exchange:
      requestConfig === undefined && response === undefined
        ? undefined
        : {
            method: requestConfig?.method?.toUpperCase(),
            url:
              requestConfig === undefined
                ? undefined
                : describeTarget(requestConfig),
            status: response?.status,
            title: detail.reported === undefined ? undefined : error.message,
          },
  };
}
