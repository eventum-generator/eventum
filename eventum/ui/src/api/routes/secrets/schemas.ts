import z from 'zod';

// Mirror of what the backend accepts as a name. A configuration
// reads a secret as `${secrets.<name>}` and is rendered to
// substitute it, so the name is read as an expression: words of
// letters, digits and `_`, separated by `.`, not starting with a
// digit. Lowercase, because the keyring folds the case of a name
// while the value is encrypted against the name as given.
export const SECRET_NAME_PATTERN = /^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$/;
export const SECRET_NAME_ERROR =
  'Only lowercase letters, digits and "_", separated by ".", each word starting with a letter or "_"';

export const SecretValueSchema = z.string();
export type SecretValue = z.infer<typeof SecretValueSchema>;

export const SecretNamesSchema = z.array(z.string());
export type SecretNames = z.infer<typeof SecretNamesSchema>;

export const SecretReferencesSchema = z.object({
  projects: z.array(z.string()),
  repositories: z.array(z.string()),
});
export type SecretReferences = z.infer<typeof SecretReferencesSchema>;

export const RenamedReferencesSchema = z.object({
  projects: z.array(z.string()),
  repositories: z.array(z.string()),
});
export type RenamedReferences = z.infer<typeof RenamedReferencesSchema>;
