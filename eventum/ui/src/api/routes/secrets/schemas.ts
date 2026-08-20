import z from 'zod';

export const SecretValueSchema = z.string();
export type SecretValue = z.infer<typeof SecretValueSchema>;

export const SecretNamesSchema = z.array(z.string());
export type SecretNames = z.infer<typeof SecretNamesSchema>;

export const SecretReferencesSchema = z.object({
  projects: z.array(z.string()),
  repositories: z.array(z.string()),
});
export type SecretReferences = z.infer<typeof SecretReferencesSchema>;

export const RepointedRepositoriesSchema = z.array(z.string());
export type RepointedRepositories = z.infer<typeof RepointedRepositoriesSchema>;
