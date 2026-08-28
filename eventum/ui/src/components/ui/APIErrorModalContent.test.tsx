import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { APIErrorModalContent } from './APIErrorModalContent';
import { APIError } from '@/api/errors';
import { renderWithProviders } from '@/test/render';

function setup(error: unknown) {
  renderWithProviders(<APIErrorModalContent error={error} />);

  return { user: userEvent.setup() };
}

/**
 * This is what a user is shown when a request fails, and it is the only
 * place the exchange behind the failure can be read: what was called,
 * what came back, and which field the backend refused. A failure that is
 * not an API error at all still has to say something rather than draw an
 * empty modal.
 */
describe('APIErrorModalContent', () => {
  it('reports what failed and why', () => {
    setup(
      new APIError({
        message: 'Invalid payload',
        details: 'Server respond with status code 422',
      })
    );

    expect(screen.getByText('Invalid payload')).toBeInTheDocument();
    expect(
      screen.getByText('Server respond with status code 422')
    ).toBeInTheDocument();
  });

  it('names the field of every problem the backend reported', () => {
    setup(
      new APIError({
        message: 'Invalid payload',
        responseValidationErrors: [
          { path: 'input.0.timer.seconds', message: 'must be a number' },
          { path: '', message: 'expected object' },
        ],
      })
    );

    expect(screen.getByText('input.0.timer.seconds')).toBeInTheDocument();
    expect(screen.getByText(/must be a number/)).toBeInTheDocument();
    expect(screen.getByText(/expected object/)).toBeInTheDocument();
  });

  it('names the request and what it answered', () => {
    setup(
      new APIError({
        message: 'Resource not found',
        requestConfig: { method: 'get', url: '/api/generators/web' },
        response: { status: 404, statusText: 'Not Found' } as never,
      })
    );

    // The line names the call and its answer together.
    expect(screen.getByText(/did not respond|responded 404/)).toHaveTextContent(
      '/api/generators/web'
    );
  });

  it('says a request never answered at all', () => {
    setup(
      new APIError({
        message: 'Server is unreachable',
        requestConfig: { method: 'post', url: '/api/generators' },
      })
    );

    // A connection that failed carries no status, and that reads
    // differently from a request the server refused.
    expect(screen.getByText(/did not respond/)).toBeInTheDocument();
  });

  it('opens the exchange as it went over the wire', async () => {
    const { user } = setup(
      new APIError({
        message: 'Invalid payload',
        requestConfig: {
          method: 'put',
          url: '/api/generator-configs/web',
          data: '{"input":[]}',
          headers: { 'content-type': 'application/json' } as never,
        },
        response: {
          status: 422,
          statusText: 'Unprocessable Entity',
          data: { detail: 'input must not be empty' },
          headers: { 'content-type': 'application/json' },
        } as never,
      })
    );

    await user.click(screen.getByText(/raw request and response/));

    expect(screen.getByText('/api/generator-configs/web')).toBeInTheDocument();
    expect(screen.getByText('422')).toBeInTheDocument();
    expect(screen.getAllByText('content-type').length).toBeGreaterThan(0);
  });

  it('reports a failure that is not an API error', () => {
    setup(new TypeError('x is not a function'));

    expect(screen.getByText(/x is not a function/)).toBeInTheDocument();
  });

  it('reports something thrown that is not an error', () => {
    setup('just a string');

    // Nothing about this is structured, and an empty modal would say
    // less than the value itself.
    expect(screen.getByText(/just a string|Unknown/)).toBeInTheDocument();
  });
});
