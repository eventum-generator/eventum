import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { installPreloadRecovery } from './preloadRecovery';

const COOLDOWN_MS = 15_000;

const noop = () => {
  // Keeps the notice of a reload out of the test output.
};

/** Fire the event the asset loader fires when a dependency fails. */
function failPreload(): VitePreloadErrorEvent {
  const event = new Event('vite:preloadError', {
    cancelable: true,
  }) as VitePreloadErrorEvent;
  event.payload = new Error(
    'Unable to preload CSS for /assets/index-DB-tz65q.css'
  );
  globalThis.dispatchEvent(event);

  return event;
}

describe('installPreloadRecovery', () => {
  let uninstall: (() => void) | undefined;

  beforeEach(() => {
    globalThis.sessionStorage.clear();
    vi.useFakeTimers();
    vi.spyOn(console, 'warn').mockImplementation(noop);
  });

  afterEach(() => {
    uninstall?.();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('reloads the document and holds back the error', () => {
    const reload = vi.fn();
    uninstall = installPreloadRecovery(reload);

    const event = failPreload();

    expect(reload).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });

  it('leaves a failure that follows a reload to the error page', () => {
    const reload = vi.fn();
    uninstall = installPreloadRecovery(reload);

    failPreload();
    vi.advanceTimersByTime(COOLDOWN_MS - 1);
    const event = failPreload();

    expect(reload).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(false);
  });

  it('reloads again once the cooldown has passed', () => {
    const reload = vi.fn();
    uninstall = installPreloadRecovery(reload);

    failPreload();
    vi.advanceTimersByTime(COOLDOWN_MS);
    const event = failPreload();

    expect(reload).toHaveBeenCalledTimes(2);
    expect(event.defaultPrevented).toBe(true);
  });

  it('reads the moment of a reload back from storage', () => {
    globalThis.sessionStorage.setItem(
      'eventum-preload-reload-at',
      String(Date.now())
    );
    const reload = vi.fn();
    uninstall = installPreloadRecovery(reload);

    const event = failPreload();

    expect(reload).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
  });

  it('does not reload when the moment cannot be kept', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage is unavailable');
    });
    const reload = vi.fn();
    uninstall = installPreloadRecovery(reload);

    const event = failPreload();

    expect(reload).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
  });

  it('stops handling failures once uninstalled', () => {
    const reload = vi.fn();
    uninstall = installPreloadRecovery(reload);

    uninstall();
    const event = failPreload();

    expect(reload).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
  });
});
