import z from 'zod';

import { GeneratorParametersSchema } from '../generators/schemas';

export const StartupGeneratorParametersSchema =
  GeneratorParametersSchema.extend({
    autostart: z.boolean().optional(),
  });
export type StartupGeneratorParameters = z.infer<
  typeof StartupGeneratorParametersSchema
>;

export const StartupGeneratorParametersListSchema = z.array(
  StartupGeneratorParametersSchema
);
export type StartupGeneratorParametersList = z.infer<
  typeof StartupGeneratorParametersListSchema
>;
