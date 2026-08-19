/**
 * Ordering of Eventum version strings.
 *
 * Versions are dotted numbers (`2.8.0`), sometimes carrying a suffix
 * that marks a version on its way to that number (`2.8.0rc1`), which
 * therefore orders before it. A missing segment counts as zero, and so
 * does anything unparsable - the ordering decides whether a browser has
 * already seen the running version, so an odd version string must leave
 * the app working rather than throw.
 */

interface Parsed {
  numbers: number[];
  /** A version on its way to those numbers rather than at them. */
  isPreRelease: boolean;
}

function parse(version: string): Parsed {
  let isPreRelease = false;

  const numbers = version.split('.').map((part) => {
    const value = Number.parseInt(part, 10);

    // A number followed by anything - `0rc1`, `0-beta` - is on its way
    // to that number. A segment that is not a number at all is just
    // unreadable, and counts as zero.
    if (/^\d+\D/.test(part.trim())) {
      isPreRelease = true;
    }

    return Number.isNaN(value) ? 0 : value;
  });

  return { numbers, isPreRelease };
}

/**
 * Compare two versions: negative when `a` is older than `b`, positive
 * when it is newer, zero when they order the same.
 */
export function compareVersions(a: string, b: string): number {
  const left = parse(a);
  const right = parse(b);
  const length = Math.max(left.numbers.length, right.numbers.length);

  for (let i = 0; i < length; i++) {
    const difference = (left.numbers[i] ?? 0) - (right.numbers[i] ?? 0);

    if (difference !== 0) {
      return difference;
    }
  }

  return Number(left.isPreRelease) * -1 - Number(right.isPreRelease) * -1;
}
