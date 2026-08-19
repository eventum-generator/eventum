import z from 'zod';

export const RepositorySchema = z.object({
  name: z.string(),
  url: z.string(),
  ref: z.string().nullish(),
  username: z.string().nullish(),
  secret: z.string().nullish(),
});
export type Repository = z.infer<typeof RepositorySchema>;

export const RepositoryStatusSchema = z.object({
  state: z.enum(['unknown', 'available', 'unavailable']),
  checked_at: z.string().nullish(),
  reason: z.string().nullish(),
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
  installed_at: z.string(),
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
  tree: z.string(),
  installed_as: z.array(InstalledProjectSchema),
});
export type CatalogEntry = z.infer<typeof CatalogEntrySchema>;

export const CatalogSchema = z.object({
  revision: z.string(),
  refreshed_at: z.string(),
  committed_at: z.string(),
  author: z.string().nullable(),
  entries: z.array(CatalogEntrySchema),
});
export type Catalog = z.infer<typeof CatalogSchema>;
