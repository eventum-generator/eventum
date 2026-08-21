import z from 'zod';

import { hasForeignToken } from '@/utils/secretReference';

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
  password: z
    .string()
    .min(1)
    .refine((value) => !hasForeignToken(value), {
      error: 'Only a "${secrets.<name>}" reference is substituted here',
    })
    .nullish(),
});
export type Repository = z.infer<typeof RepositorySchema>;

// A moment the server stamps arrives in UTC, while the time a commit
// was authored at carries the offset of whoever authored it, so every
// moment here is read with an offset allowed.
const moment = () => z.iso.datetime({ offset: true });

export const RepositoryStatusSchema = z.object({
  state: z.enum(['unknown', 'available', 'unavailable']),
  checked_at: moment().nullable(),
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
  installed_at: moment(),
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
  refreshed_at: moment(),
  committed_at: moment(),
  author: z.string().nullable(),
  entries: z.array(CatalogEntrySchema),
});
export type Catalog = z.infer<typeof CatalogSchema>;

// What a repository publishing generators in the open says about
// itself, republished by the instance as it was read.
export const DiscoveredRepositorySchema = z.object({
  name: z.string(),
  full_name: z.string(),
  url: z.string(),
  page_url: z.string(),
  owner: z.string(),
  description: z.string().nullable(),
  topics: z.array(z.string()),
  stars: z.number().int(),
  updated_at: moment().nullable(),
  license: z.string().nullable(),
  archived: z.boolean(),
  official: z.boolean(),
  connected: z.boolean(),
});
export type DiscoveredRepository = z.infer<typeof DiscoveredRepositorySchema>;

export const DiscoveryRateSchema = z.object({
  remaining: z.number().int().nullable(),
  reset_at: moment().nullable(),
});
export type DiscoveryRate = z.infer<typeof DiscoveryRateSchema>;

export const DiscoverySchema = z.object({
  topic: z.string(),
  query: z.string(),
  entries: z.array(DiscoveredRepositorySchema),
  total_count: z.number().int(),
  refreshed_at: moment(),
  rate: DiscoveryRateSchema,
});
export type Discovery = z.infer<typeof DiscoverySchema>;
