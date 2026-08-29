/**
 * Recovery from an asset the browser failed to load.
 *
 * Every page is a lazily imported chunk, and the stylesheet of a chunk
 * arrives through a `<link>` element appended on demand. A chunk or a
 * stylesheet that never arrives rejects the import, and the router is
 * left with nothing to render but the error page - even though the rest
 * of the app is intact and the next attempt usually succeeds.
 *
 * The document is reloaded instead. Retrying the import in place cannot
 * work: the loader remembers every dependency it has attempted and
 * leaves the failed `<link>` in the document, so a repeated import
 * skips the stylesheet and renders the page unstyled. Only a fresh
 * document requests it again.
 *
 * A reload that does not help must not turn into a loop, so the moment
 * of one is kept for the tab and a failure that follows it too closely
 * is left to the error page.
 */

const RELOAD_COOLDOWN_MS = 15_000;

const LAST_RELOAD_KEY = 'eventum-preload-reload-at';

/** Read the moment of the last reload, `null` if there was none. */
function readLastReload(): number | null {
  let stored: string | null;
  try {
    stored = globalThis.sessionStorage.getItem(LAST_RELOAD_KEY);
  } catch {
    return null;
  }

  if (stored === null) {
    return null;
  }

  const at = Number.parseInt(stored, 10);

  return Number.isNaN(at) ? null : at;
}

/** Keep the moment of a reload, reporting whether it was kept. */
function keepLastReload(at: number): boolean {
  try {
    globalThis.sessionStorage.setItem(LAST_RELOAD_KEY, String(at));
    return true;
  } catch {
    // A moment that cannot be kept cannot bound the reloads either.
    return false;
  }
}

function handlePreloadError(
  event: VitePreloadErrorEvent,
  reload: () => void
): void {
  const now = Date.now();
  const lastReload = readLastReload();

  if (lastReload !== null && now - lastReload < RELOAD_COOLDOWN_MS) {
    return;
  }

  if (!keepLastReload(now)) {
    return;
  }

  console.warn('Reloading after a failed asset load', event.payload);

  // Keeps the loader from rethrowing the error into the router, which
  // would draw the error page over the document being replaced.
  event.preventDefault();
  reload();
}

/**
 * Start recovering from failed asset loads, returning the call that
 * stops it. `reload` replaces the document, by default the current one.
 */
export function installPreloadRecovery(
  reload: () => void = () => {
    globalThis.location.reload();
  }
): () => void {
  const listener = (event: VitePreloadErrorEvent) => {
    handlePreloadError(event, reload);
  };

  globalThis.addEventListener('vite:preloadError', listener);

  return () => {
    globalThis.removeEventListener('vite:preloadError', listener);
  };
}
