import z from 'zod';

export const RepositorySchema = z.object({
  name: z.string(),
  url: z.string(),
  ref: z.string().nullish(),
  username: z.string().nullish(),
  secret: z.string().nullish(),
});
export type Repository = z.infer<typeof RepositorySchema>;

export const RepositoriesSchema = z.array(RepositorySchema);
export type Repositories = z.infer<typeof RepositoriesSchema>;

export const CatalogEntrySchema = z.object({
  name: z.string(),
  title: z.string().nullable(),
  summary: z.string().nullable(),
  file_count: z.number().int(),
  size: z.number().int(),
});
export type CatalogEntry = z.infer<typeof CatalogEntrySchema>;

export const CatalogSchema = z.object({
  revision: z.string(),
  refreshed_at: z.string(),
  entries: z.array(CatalogEntrySchema),
});
export type Catalog = z.infer<typeof CatalogSchema>;
