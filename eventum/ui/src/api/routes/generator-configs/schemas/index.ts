import { z } from 'zod';

import { EventPluginNamedConfigSchema } from './plugins/event';
import { InputPluginNamedConfigSchema } from './plugins/input';
import { OutputPluginNamedConfigSchema } from './plugins/output';

export const GeneratorDirsExtendedInfoSchema = z.array(
  z.object({
    name: z.string(),
    size_in_bytes: z.number().int().nullable(),
    last_modified: z.number().nullable(),
    generator_ids: z.array(z.string()),
  })
);

export type GeneratorDirsExtendedInfo = z.infer<
  typeof GeneratorDirsExtendedInfoSchema
>;

const InputPluginsNamedConfigSchema = z
  .array(InputPluginNamedConfigSchema)
  .min(1);
export type InputPluginsNamedConfig = z.infer<
  typeof InputPluginsNamedConfigSchema
>;

const OutputPluginsNamedConfigSchema = z
  .array(OutputPluginNamedConfigSchema)
  .min(1);
export type OutputPluginsNamedConfig = z.infer<
  typeof OutputPluginsNamedConfigSchema
>;

export const GeneratorConfigSchema = z.object({
  input: InputPluginsNamedConfigSchema,
  event: EventPluginNamedConfigSchema,
  output: OutputPluginsNamedConfigSchema,
});
export type GeneratorConfig = z.infer<typeof GeneratorConfigSchema>;

export const GeneratorConfigPathSchema = z.string();
export type GeneratorConfigPath = z.infer<typeof GeneratorConfigPathSchema>;

const FileNodeSchema: z.ZodType = z.lazy(() =>
  z.object({
    name: z.string(),
    is_dir: z.boolean(),
    size_in_bytes: z.number().int().nullable(),
    children: z.array(FileNodeSchema).nullable().optional(),
  })
);
export interface FileNode {
  name: string;
  is_dir: boolean;
  // Set for files only, and null when the size cannot be read.
  size_in_bytes: number | null;
  children: FileNode[] | null;
}

export const FileNodesListSchema = z.array(FileNodeSchema);
export type FileNodesList = z.infer<typeof FileNodesListSchema>;

export const GeneratorFileContentSchema = z.string();
export type GeneratorFileContent = z.infer<typeof GeneratorFileContentSchema>;
