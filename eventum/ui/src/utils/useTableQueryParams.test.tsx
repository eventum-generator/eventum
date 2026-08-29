import { act, renderHook } from '@testing-library/react';
import { FC, ReactNode } from 'react';
import {
  MemoryRouter,
  RouterProvider,
  createMemoryRouter,
  useLocation,
} from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { useTableQueryParams } from './useTableQueryParams';
import { renderWithProviders } from '@/test/render';

type Params = ReturnType<typeof useTableQueryParams>;

let params: Params;

/** Hands the hook out of a route, so the router can be inspected. */
const Params: FC<{ onReady: (value: Params) => void }> = ({ onReady }) => {
  onReady(useTableQueryParams());

  return null;
};

function wrapperAt(initial: string): FC<{ children: ReactNode }> {
  return ({ children }) => (
    <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>
  );
}

function renderParams(initial = '/instances') {
  return renderHook(
    () => ({
      params: useTableQueryParams(),
      location: useLocation(),
    }),
    { wrapper: wrapperAt(initial) }
  );
}

/**
 * Table filters live in the URL so a shared link restores them. Each
 * handler writes only its own key, which makes the merge the whole
 * point: a write that replaced the query string instead would clear
 * every other filter on the screen.
 */
describe('useTableQueryParams', () => {
  it('reads the filters already in the URL', () => {
    const { result } = renderParams('/instances?instance=web&status=active');

    expect(result.current.params.searchParams.get('instance')).toBe('web');
    expect(result.current.params.searchParams.get('status')).toBe('active');
  });

  it('keeps the keys it was not given', () => {
    const { result } = renderParams('/instances?instance=web&status=active');

    act(() => {
      result.current.params.setParams({ instance: 'db' });
    });

    expect(result.current.params.searchParams.get('instance')).toBe('db');
    expect(result.current.params.searchParams.get('status')).toBe('active');
  });

  it('writes several keys in one go', () => {
    const { result } = renderParams();

    act(() => {
      result.current.params.setParams({ usage: 'unused', instances: null });
    });

    expect(result.current.location.search).toBe('?usage=unused');
  });

  it.each([
    ['null', null],
    ['an empty string', ''],
    ['an empty list', [] as string[]],
  ])('drops a key set to %s', (_label, value) => {
    const { result } = renderParams('/projects?q=web');

    act(() => {
      result.current.params.setParams({ q: value });
    });

    expect(result.current.params.searchParams.has('q')).toBe(false);
  });

  it('leaves a key set to undefined untouched', () => {
    const { result } = renderParams('/projects?q=web');

    act(() => {
      result.current.params.setParams({ q: undefined });
    });

    expect(result.current.params.searchParams.get('q')).toBe('web');
  });

  it('joins a list into one comma-separated value', () => {
    const { result } = renderParams();

    act(() => {
      result.current.params.setParams({ instances: ['web', 'db'] });
    });

    expect(result.current.params.searchParams.get('instances')).toBe('web,db');
  });

  it('replaces the entry instead of stacking one per keystroke', () => {
    const router = createMemoryRouter(
      [
        {
          path: '/projects',
          element: <Params onReady={(value) => (params = value)} />,
        },
      ],
      { initialEntries: ['/projects'] }
    );

    renderWithProviders(<RouterProvider router={router} />);

    for (const query of ['w', 'we', 'web']) {
      act(() => {
        params.setParams({ q: query });
      });
    }

    expect(params.searchParams.get('q')).toBe('web');
    // Three writes, one entry: going back has to leave the table, not
    // walk the query string backwards a character at a time.
    expect(router.state.historyAction).toBe('REPLACE');
    expect(router.window?.history.length ?? 1).toBe(1);
  });
});
