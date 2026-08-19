# UI Rules

Eventum Studio is a React + TypeScript SPA built on Mantine, react-query, Zod, and Vite.

## Directory layout

- `ui/src/pages/<PageName>/` - one folder per routable page, nested features as subfolders.
- `ui/src/components/{ui,layout,modals,state}/` - shared pieces by kind.
- `ui/src/api/routes/<resource>/` - API wrappers and Zod schemas per backend resource.
- `ui/src/api/hooks/` - react-query hooks per resource.
- `ui/src/routing/config.tsx` - route definitions; pages are lazy-loaded.
- `ui/src/releases/` - the release panels shown after an upgrade, and the animated scenes they are drawn from.

## Theming

`ui/src/theme/index.ts` is the single source of colour, radius and shadow. Everything else reads Mantine CSS variables - the app defines no colour tokens of its own.

- **Palettes.** Each scale is a normal 10-shade Mantine ramp (0 lightest -> 9 darkest). `primaryShade` is `{ light: 6, dark: 5 }`, so shade 6 carries a role's light-scheme colour and shade 4 its dark-scheme one. Mantine then derives `-filled`, `-text`, `-light`, `-light-color` per scheme; never hand-pick a shade index at a call site.
- **Neutrals.** The `dark` and `gray` ramps drive the whole chrome: `--mantine-color-body` (panels), `--mantine-color-default` (controls, dropdowns), `--mantine-color-default-hover`, `--mantine-color-default-border`, `--mantine-color-text`, `--mantine-color-dimmed`. `--ev-canvas` is the one app variable Mantine has no equivalent for - the page background behind the panels.
- **Semantics.** Danger, success, warning and info are the `red` / `green` / `yellow` / `blue` palettes. A status chip carries a palette only while its instance is live; the states at rest share the neutral chip and name their outcome through the indicator alone, at a shade deep enough to read as switched off. Use the colour prop (`c="red"`, `color="green"`) over a raw variable wherever a Mantine component accepts one.
- **Radius.** Two tiers: `md` for controls, `lg` for panels and modals (a `Paper` default). Don't set `radius` per call site.
- **Order of override.** Theme `components` (`defaultProps`, `vars`) first; `cssVariablesResolver` for a variable Mantine resolves wrongly; a rule in `theme/components.css` only for parts with no variable at all.

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
- A `Switch` has no "unset" state, and configurations arrive without their unset fields. Set `checked` to fall back to the backend default, otherwise a field the user never touched is drawn as off whatever the plugin does.
- For validation that only makes sense in the UI (e.g. friendlier error messages), extend the schema inside the form component. Don't touch the canonical schema under `api/routes/`.

## Editor autocomplete

- `globals.ts` under `pages/ProjectPage/common/EditorTab/FileEditor/completions/` is the single source for Jinja template autocomplete.
- Mirror there any backend change that exposes new template context variables or module functions.

## Tests

`pnpm test` runs vitest over `src/**/*.test.{ts,tsx}` in jsdom. Tests sit next to the code they cover.

- `src/test/setup.ts` - jest-dom matchers, unmount after each test, and the jsdom stubs the app mounts against (`matchMedia`, `ResizeObserver`, `IntersectionObserver`).
- `src/test/render.tsx` - `renderWithProviders` mounts a component under the app theme and a query client of its own; page-specific providers are wrapped at the call site.
- Data comes from mocking the `api/hooks/` module the component reads - tests never reach the network.
- Drive interaction through `@testing-library/user-event`. Nothing in jsdom is laid out, so anything resting on real geometry belongs in a browser instead.
