// What a value naming a keyring secret looks like, and what it takes
// to tell that from a value carrying the credential itself. The
// backend reads the same shapes out of a password, so these mirror
// the tokens it substitutes.

// A substitution token of any kind.
const TOKEN_PATTERN = /\$\{\s*([^\s}]+)\s*\}/g;

// A value that is nothing but a reference to a keyring secret. The
// backend tolerates spacing inside the token, so this does too.
const REFERENCE_PATTERN = /^\$\{\s*secrets\.[^\s}]+\s*\}$/;

/**
 * Whether the value only names a keyring secret. Padding is part of
 * the value rather than of the token, so a padded reference reads as
 * a value of its own - which is how the backend resolves it.
 */
export function isSecretReference(value: string | undefined): boolean {
  return value !== undefined && REFERENCE_PATTERN.test(value);
}

/**
 * Whether a secret of this name can be referenced at all. A name
 * holding a space or a closing brace cannot be written as a token, so
 * the reference of it would travel as the password itself.
 */
export function isReferenceable(name: string): boolean {
  return /^[^\s}]+$/.test(name);
}

/**
 * Whether the value holds a token naming something other than a
 * keyring secret. Only a secret is substituted, so any other token
 * would reach the destination as part of the value itself.
 */
export function hasForeignToken(value: string): boolean {
  return [...value.matchAll(TOKEN_PATTERN)].some(
    (match) => !/^secrets\..+$/.test(match[1] ?? '')
  );
}

/** The reference a secret of this name is written as. */
export function secretReference(name: string): string {
  return `\${secrets.${name}}`;
}
