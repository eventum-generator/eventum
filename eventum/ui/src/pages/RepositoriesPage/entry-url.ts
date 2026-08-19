/**
 * Address of a published generator on the host that serves the
 * repository.
 *
 * Only the hosts whose layout is known are linked to; anywhere else
 * the path inside the repository is all that can be stated, and a
 * guessed link that leads nowhere is worse than none.
 */
export function buildEntryUrl(
  url: string,
  ref: string | null | undefined,
  path: string
): string | null {
  let parsed: URL;

  try {
    parsed = new URL(url);
  } catch {
    return null;
  }

  const repository = parsed.pathname
    .split('/')
    .filter(Boolean)
    .join('/')
    .replace(/\.git$/, '');
  const base = `${parsed.origin}/${repository}`;
  const revision = ref ?? 'HEAD';
  const host = parsed.hostname.toLowerCase();

  if (host === 'github.com' || host.endsWith('.githubusercontent.com')) {
    return `${base}/tree/${encodeURIComponent(revision)}/${path}`;
  }

  if (host === 'gitlab.com' || host.startsWith('gitlab.')) {
    return `${base}/-/tree/${encodeURIComponent(revision)}/${path}`;
  }

  return null;
}
