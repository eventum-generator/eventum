---
paths:
  - "eventum/ui/src/**/*.{ts,tsx}"
---

# UI Rules

Eventum Studio is a React + TypeScript SPA built on Mantine, react-query, Zod, and Vite.

## Directory layout

- `ui/src/pages/<PageName>/` - one folder per routable page, nested features as subfolders.
- `ui/src/components/{ui,layout,modals,state}/` - shared pieces by kind.
- `ui/src/api/routes/<resource>/` - API wrappers and Zod schemas per backend resource.
- `ui/src/api/hooks/` - react-query hooks per resource.
- `ui/src/routing/config.tsx` - route definitions; pages are lazy-loaded.

## Icons

- Standard icons: `@tabler/icons-react`.
- Brand icons: `@icons-pack/react-simple-icons`, wrapped with `brandIcon()`.

## Zod schemas

On the API boundary, every backend Pydantic model has a mirror Zod schema - same field names, types, and constraints. Keep them in sync when the backend changes.

- Non-string config fields (boolean, number, enum) wrap in `orPlaceholder(...)` so forms accept `${params.*}` / `${secrets.*}` placeholder strings the backend resolves at runtime.

## API hooks

- Route functions validate responses against their Zod schema before returning - untyped data never reaches components.

## Plugin UI

Adding or modifying a plugin touches four places.

- **Zod schema** for the plugin config.
- **Schema union** - add the schema to `schemas/plugins/<type>/index.ts`.
- **Form component** under `pages/ProjectPage/<Type>PluginTab/<Type>PluginParams/`.
- **Registry entry** in `modules/plugins/registry.ts` - metadata, default config, and default assets (optional).

## Forms

- Wire inputs via `@mantine/form` + `zod4Resolver` so Zod errors surface as field errors.
- Forms propagate changes through a parent `onChange` callback, not a submit.
- Empty inputs for optional fields must land as `undefined`, not empty strings.
- For validation that only makes sense in the UI (e.g. friendlier error messages), extend the schema inside the form component. Don't touch the canonical schema under `api/routes/`.

## Editor autocomplete

- `globals.ts` under `pages/ProjectPage/common/EditorTab/FileEditor/completions/` is the single source for Jinja template autocomplete.
- Mirror there any backend change that exposes new template context variables or module functions.
