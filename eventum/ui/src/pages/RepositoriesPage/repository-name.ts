import { REPOSITORY_NAME_PATTERN } from '@/api/routes/repositories/schemas';

/** What a connected repository may be named with. */
const ALLOWED = /[a-zA-Z0-9._-]/;

/** What such a name may begin and end with. */
const EDGE = /[a-zA-Z0-9]/;

/** How many names are tried before the taken one is offered anyway. */
const MAX_SUFFIX = 100;

/** Replace what a name may not hold, character by character - a
 *  pattern over the whole string would scan it for every position. */
function fold(value: string): string {
  let folded = '';

  for (const character of value) {
    folded += ALLOWED.test(character) ? character : '-';
  }

  return folded;
}

/** Cut what a name may not begin or end with. */
function trimEdges(value: string): string {
  let start = 0;
  let end = value.length;

  while (start < end && !EDGE.test(value.charAt(start))) start += 1;
  while (end > start && !EDGE.test(value.charAt(end - 1))) end -= 1;

  return value.slice(start, end);
}

/**
 * Propose a name to connect a published repository under.
 *
 * The name a repository carries on its host is what the user would
 * type anyway, so it is offered - folded to what a name may hold, and
 * with a suffix when that name is taken, so the dialog opens ready to
 * submit rather than on an error about a name nobody chose.
 */
export function proposeRepositoryName(
  repositoryName: string,
  existingNames: string[]
): string {
  const base = trimEdges(fold(repositoryName));

  if (!base || !REPOSITORY_NAME_PATTERN.test(base)) return '';

  if (!existingNames.includes(base)) return base;

  for (let suffix = 2; suffix <= MAX_SUFFIX; suffix++) {
    const candidate = `${base}-${suffix}`;

    if (!existingNames.includes(candidate)) return candidate;
  }

  return base;
}
