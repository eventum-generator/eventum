import { z } from 'zod';

const StateFieldNameSchema = z.string().regex(/^(locals|shared|globals)\..+$/);

function checkIsSingleProp(value: object): boolean {
  return Object.keys(value).length === 1;
}

const EqSchema = z.object({
  eq: z.record(StateFieldNameSchema, z.any()).refine(checkIsSingleProp),
});

const GtSchema = z.object({
  gt: z.record(StateFieldNameSchema, z.number()).refine(checkIsSingleProp),
});

const GeSchema = z.object({
  ge: z.record(StateFieldNameSchema, z.number()).refine(checkIsSingleProp),
});

const LtSchema = z.object({
  lt: z.record(StateFieldNameSchema, z.number()).refine(checkIsSingleProp),
});

const LeSchema = z.object({
  le: z.record(StateFieldNameSchema, z.number()).refine(checkIsSingleProp),
});

const LenEqSchema = z.object({
  len_eq: z
    .record(StateFieldNameSchema, z.number().int())
    .refine(checkIsSingleProp),
});

const LenGtSchema = z.object({
  len_gt: z
    .record(StateFieldNameSchema, z.number().int())
    .refine(checkIsSingleProp),
});

const LenGeSchema = z.object({
  len_ge: z
    .record(StateFieldNameSchema, z.number().int())
    .refine(checkIsSingleProp),
});

const LenLtSchema = z.object({
  len_lt: z
    .record(StateFieldNameSchema, z.number().int())
    .refine(checkIsSingleProp),
});

const LenLeSchema = z.object({
  len_le: z
    .record(StateFieldNameSchema, z.number().int())
    .refine(checkIsSingleProp),
});

const ContainsSchema = z.object({
  contains: z.record(StateFieldNameSchema, z.any()).refine(checkIsSingleProp),
});

const InSchema = z.object({
  in: z.record(StateFieldNameSchema, z.any()).refine(checkIsSingleProp),
});

const HasTagsSchema = z.object({
  has_tags: z.union([z.string().min(1), z.array(z.string().min(1)).min(1)]),
});

const TimestampComponentsSchema = z.object({
  year: z.number().int().gte(0).lte(10_000).nullable().optional(),
  month: z.number().int().gte(1).lte(12).nullable().optional(),
  day: z.number().int().gte(1).lte(31).nullable().optional(),
  hour: z.number().int().gte(0).lt(24).nullable().optional(),
  minute: z.number().int().gte(0).lt(60).nullable().optional(),
  second: z.number().int().gte(0).lt(60).nullable().optional(),
  microsecond: z.number().int().gte(0).lt(1_000_000).nullable().optional(),
});

const BeforeSchema = z.object({
  before: TimestampComponentsSchema,
});

const AfterSchema = z.object({
  after: TimestampComponentsSchema,
});

const MatchesSchema = z.object({
  matches: z.record(StateFieldNameSchema, z.string()).refine(checkIsSingleProp),
});

const DefinedSchema = z.object({
  defined: StateFieldNameSchema,
});

const AlwaysSchema = z.object({
  always: z.null(),
});

const NeverSchema = z.object({
  never: z.null(),
});

const ConditionCheckSchema = z.union([
  EqSchema,
  GtSchema,
  GeSchema,
  LtSchema,
  LeSchema,
  MatchesSchema,
  LenEqSchema,
  LenGtSchema,
  LenGeSchema,
  LenLtSchema,
  LenLeSchema,
  ContainsSchema,
  InSchema,
  BeforeSchema,
  AfterSchema,
  DefinedSchema,
  HasTagsSchema,
  AlwaysSchema,
  NeverSchema,
]);

const OrSchema = z.object({
  or: z.array(z.lazy(() => ConditionSchema)).min(2),
});

const AndSchema = z.object({
  and: z.array(z.lazy(() => ConditionSchema)).min(2),
});

const NotSchema = z.object({
  not: z.lazy(() => ConditionSchema),
});

const ConditionLogicSchema: z.ZodType = z.lazy(() =>
  z.union([OrSchema, AndSchema, NotSchema])
);

export const ConditionSchema = z.union([
  ConditionCheckSchema,
  ConditionLogicSchema,
]);
