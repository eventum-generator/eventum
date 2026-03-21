---
description: Rules for React/TypeScript UI code (Eventum Studio)
globs:
  - "eventum/ui/**"
---

# UI Development Rules

## Zod Schema Conventions

- Schemas live in `ui/src/api/routes/generator-configs/schemas/plugins/<type>/configs/`.
- Mirror the Python Pydantic model exactly: same field names, same constraints, same discriminators.
- Use `z.discriminatedUnion('type', [...])` for polymorphic configs (same pattern as Pydantic `Field(discriminator=...)`).
- Export both the schema (`FooSchema`) and its inferred type (`type Foo = z.infer<typeof FooSchema>`).
- Enum values must match the Python `StrEnum` values exactly.

### `orPlaceholder()` Helper

- Located in `schemas/placeholder.ts`.
- Wraps any Zod type to also accept `${params.*}` / `${secrets.*}` placeholder strings.
- Use on non-string fields (booleans, numbers, enums) that may receive placeholder substitution.
- String fields do NOT need `orPlaceholder` -- they already accept strings.

## Plugin Registry (`modules/plugins/registry.ts`)

When adding a new plugin, update ALL of these in the registry file:

1. **Info record** (`INPUT_PLUGINS_INFO` / `EVENT_PLUGINS_INFO` / `OUTPUT_PLUGINS_INFO`) -- label, icon, description.
2. **Default config** (`INPUT_PLUGIN_DEFAULT_CONFIGS` / etc.) -- import and add the default config.
3. **Default assets** (for event plugins in `EVENT_PLUGIN_DEFAULT_ASSETS`) -- template/script/data file path and content.
4. The `satisfies Record<PluginName, ...>` constraint will catch missing entries at compile time.

## Icons

- Use `@tabler/icons-react` for standard icons.
- Use `@icons-pack/react-simple-icons` for brand icons (wrapped with `brandIcon()` to scale down).

## Form Components

- Plugin form components live in `ui/src/pages/ProjectPage/<Type>PluginTab/<Type>PluginParams/`.
- One component per plugin config type.
- Forms read/write the Zod-validated config object.

## Editor Autocomplete (`globals.ts`)

- Path: `ui/src/pages/ProjectPage/common/EditorTab/FileEditor/completions/globals.ts`
- Contains autocomplete entries for template context variables and module functions.
- Must be updated when adding: new context variables, new module functions, new template features.

## Three Touch Points for Template Plugin Changes

When modifying template plugin features, update all three:

1. **Zod schemas**: `ui/src/api/routes/generator-configs/schemas/plugins/event/configs/template/index.ts`
2. **UI form**: `ui/src/pages/ProjectPage/EventPluginTab/EventPluginParams/TemplateEventPluginParams/TemplatesSection/TemplateParams.tsx`
3. **Editor autocomplete**: `ui/src/pages/ProjectPage/common/EditorTab/FileEditor/completions/globals.ts`
