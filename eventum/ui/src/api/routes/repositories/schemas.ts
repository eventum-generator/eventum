import z from 'zod';

// Mirrors of the constraints the backend enforces, so a value it
// would refuse is named as a field error rather than coming back as
// an unplaced 422.
export const REPOSITORY_NAME_PATTERN =
  /^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$/;
export const REPOSITORY_REF_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/;

export const RepositorySchema = z.object({
  name: z.string().min(1).max(64).regex(REPOSITORY_NAME_PATTERN),
  url: z.string().min(1).max(2048),
  ref: z.string().min(1).max(255).regex(REPOSITORY_REF_PATTERN).nullish(),
  username: z.string().min(1).max(255).nullish(),
  secret: z.string().min(1).max(255).nullish(),
});
export type Repository = z.infer<typeof RepositorySchema>;

export const RepositoryStatusSchema = z.object({
  state: z.enum(['unknown', 'available', 'unavailable']),
  checked_at: z.iso.datetime().nullable(),
  reason: z.string().nullable(),
});
export type RepositoryStatus = z.infer<typeof RepositoryStatusSchema>;

export const ConnectedRepositorySchema = RepositorySchema.extend({
  status: RepositoryStatusSchema,
});
export type ConnectedRepository = z.infer<typeof ConnectedRepositorySchema>;

export const ConnectedRepositoriesSchema = z.array(ConnectedRepositorySchema);
export type ConnectedRepositories = z.infer<typeof ConnectedRepositoriesSchema>;

export const InstalledProjectSchema = z.object({
  project: z.string(),
  revision: z.string(),
  installed_at: z.iso.datetime(),
  outdated: z.boolean(),
});
export type InstalledProject = z.infer<typeof InstalledProjectSchema>;

export const CatalogEntrySchema = z.object({
  name: z.string(),
  path: z.string(),
  title: z.string().nullable(),
  summary: z.string().nullable(),
  file_count: z.number().int(),
  size: z.number().int(),
  installed_as: z.array(InstalledProjectSchema),
});
export type CatalogEntry = z.infer<typeof CatalogEntrySchema>;

export const CatalogSchema = z.object({
  revision: z.string(),
  refreshed_at: z.iso.datetime(),
  committed_at: z.iso.datetime(),
  author: z.string().nullable(),
  entries: z.array(CatalogEntrySchema),
});
export type Catalog = z.infer<typeof CatalogSchema>;
