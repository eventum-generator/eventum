import axios, { AxiosError } from 'axios';

import { APIError } from './errors';

// Deadline for a regular request. Long enough for the directory walks
// and preview runs the backend performs on request, short enough to
// surface an unresponsive backend.
const DEFAULT_TIMEOUT = 60_000;

// Deadline for a request that transfers file content. How long such a
// request takes is set by the size of the file and the speed of the
// link, not by the health of the backend, so any fixed deadline would
// cut off a transfer that is still making progress. Zero disables the
// deadline; a broken connection still fails the request.
export const TRANSFER_TIMEOUT = 0;

export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_TIMEOUT,
});

// User friendly titles of response codes that make sense to distinguish
function describeStatusCode(statusCode: number): string {
  if (statusCode >= 500) {
    return 'Server error';
  } else if (statusCode === 401) {
    return 'Invalid credentials';
  } else if (statusCode === 403) {
    return 'Forbidden';
  } else if (statusCode === 404) {
    return 'Resource not found';
  } else if (statusCode === 409) {
    return 'Resource already exists';
  } else if (statusCode === 413) {
    return 'Content too large';
  } else if (statusCode === 422) {
    return 'Invalid payload';
  } else {
    return 'Client error';
  }
}

// A request that never reached a response either ran out of its
// deadline or failed on the connection - the two read differently to
// the user.
function describeFailedRequest(error: AxiosError): string {
  const timedOut =
    error.code === AxiosError.ECONNABORTED ||
    error.code === AxiosError.ETIMEDOUT;

  return timedOut ? 'Request timed out' : 'Request failed';
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (error instanceof AxiosError) {
      if (error.response === undefined) {
        return Promise.reject(
          new APIError({
            message: describeFailedRequest(error),
            details: error.message,
            requestConfig: error.config,
          })
        );
      }

      const statusCode = error.response.status;

      return Promise.reject(
        new APIError({
          message: describeStatusCode(statusCode),
          details: `Server respond with status code ${statusCode}`,
          response: error.response,
          requestConfig: error.config,
        })
      );
    } else if (error instanceof Error) {
      return Promise.reject(
        new APIError({ message: 'Unexpected error', details: error.message })
      );
    } else {
      return Promise.reject(new APIError({ message: 'Unknown error' }));
    }
  }
);
