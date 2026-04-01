import z from 'zod';

export const GlobalsReferenceSchema = z.object({
  key: z.string(),
  template: z.string(),
});
export type GlobalsReference = z.infer<typeof GlobalsReferenceSchema>;

export const GlobalsWarningSchema = z.object({
  type: z.enum(['dynamic_key', 'update_call']),
  template: z.string(),
});
export type GlobalsWarning = z.infer<typeof GlobalsWarningSchema>;

export const GlobalsUsageSchema = z.object({
  writes: z.array(GlobalsReferenceSchema),
  reads: z.array(GlobalsReferenceSchema),
  warnings: z.array(GlobalsWarningSchema),
});
export type GlobalsUsage = z.infer<typeof GlobalsUsageSchema>;

export const ScenarioResponseSchema = z.object({
  name: z.string(),
  generator_ids: z.array(z.string()),
});
export type ScenarioResponse = z.infer<typeof ScenarioResponseSchema>;
