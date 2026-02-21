import z from 'zod';

/**
 * Schema that matches `${params.*}` and `${secrets.*}` placeholder strings
 * used for variable substitution in generator configs.
 */
export const PlaceholderStringSchema = z
  .string()
  .regex(/^\$\{(params|secrets)\..+\}$/);

/**
 * Wraps a Zod schema to also accept placeholder strings.
 * Use this for non-string fields (URLs, booleans, numbers, enums)
 * in plugin config schemas.
 */
export function orPlaceholder<T extends z.ZodType>(schema: T) {
  return z.union([schema, PlaceholderStringSchema]);
}
