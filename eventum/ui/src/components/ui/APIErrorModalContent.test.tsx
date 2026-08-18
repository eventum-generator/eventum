import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosResponse } from 'axios';
import { describe, expect, it } from 'vitest';

import { APIErrorModalContent } from './APIErrorModalContent';
import { APIError } from '@/api/errors';
import { renderWithProviders } from '@/test/render';

function makeError(detail: unknown): APIError {
  return new APIError({
    message: 'Resource already exists',
    details: 'Server respond with status code 409',
    response: {
      status: 409,
      statusText: '',
      data: { detail },
      headers: { 'content-type': 'application/json' },
      config: {},
    } as unknown as AxiosResponse,
    requestConfig: {
      baseURL: '/api',
      url: '/generator-configs/demo/name',
      method: 'post',
      headers: { Accept: 'application/json' },
      data: '{"name":"renamed"}',
    },
  });
}

function precedes(first: HTMLElement, second: HTMLElement): boolean {
  return (
    (first.compareDocumentPosition(second) &
      Node.DOCUMENT_POSITION_FOLLOWING) !==
    0
  );
}

describe('APIErrorModalContent', () => {
  it('puts the sentence the server sent above the status line', () => {
    renderWithProviders(
      <APIErrorModalContent
        error={makeError('Instances using the project must be stopped')}
      />
    );

    const reported = screen.getByText(
      'Instances using the project must be stopped'
    );
    const exchange = screen.getByText(/responded 409 Resource already exists/);

    expect(precedes(reported, exchange)).toBe(true);
  });

  it('keeps the raw exchange out of the way until it is asked for', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <APIErrorModalContent error={makeError('Project is in use')} />
    );

    const collapsed = screen
      .getByText('POST')
      .closest('[style*="display: none"]');
    expect(collapsed).not.toBeNull();

    await user.click(screen.getByText('Show raw request and response'));

    expect(screen.getByText('Hide raw request and response')).toBeVisible();
    expect(
      screen.getByText('/api/generator-configs/demo/name')
    ).toBeInTheDocument();
    expect(screen.getByText('409')).toBeInTheDocument();
  });

  it('lists the fields of a rejected payload', () => {
    renderWithProviders(
      <APIErrorModalContent
        error={makeError([
          { loc: ['body', 'name'], msg: 'Field required', type: 'missing' },
        ])}
      />
    );

    const issue = screen.getByText('body.name').closest('p');
    expect(issue?.textContent).toBe('body.name Field required');
  });

  it('renders a plain error by its message', () => {
    renderWithProviders(<APIErrorModalContent error={new Error('Boom')} />);

    expect(screen.getByText('Boom')).toBeInTheDocument();
  });

  it('reports the type of a thrown value that is not an error', () => {
    renderWithProviders(<APIErrorModalContent error={'oops'} />);

    expect(screen.getByText('Unknown error: string')).toBeInTheDocument();
  });
});
