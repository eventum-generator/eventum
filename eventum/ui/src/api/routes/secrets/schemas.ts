import z from 'zod';

// Mirror of what the backend accepts as a name. A configuration
// reads a secret as `${secrets.<name>}` and is rendered to
// substitute it, so the name is read as an expression: words of
// letters, digits and `_`, separated by `.`, not starting with a
// digit. `\w` is ASCII here, so it is the same set the backend
// spells out.
export const SECRET_NAME_PATTERN = /^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$/;
export const SECRET_NAME_ERROR =
  'Only letters, digits and "_" are allowed, separated by "."';

export const SecretValueSchema = z.string();
export type SecretValue = z.infer<typeof SecretValueSchema>;

export const SecretNamesSchema = z.array(z.string());
export type SecretNames = z.infer<typeof SecretNamesSchema>;
