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

  // A branch name may hold slashes, and they are path separators in
  // the address as well - escaping them whole turns "release/1.0"
  // into a page neither host serves.
  const revision = (ref ?? 'HEAD')
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const host = parsed.hostname.toLowerCase();

  if (host === 'github.com') {
    return `${base}/tree/${revision}/${path}`;
  }

  if (host === 'gitlab.com' || host.startsWith('gitlab.')) {
    return `${base}/-/tree/${revision}/${path}`;
  }

  return null;
}
