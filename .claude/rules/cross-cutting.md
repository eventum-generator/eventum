---
description: Cross-cutting change checklist enforced on every change
alwaysApply: true
---

# Cross-cutting Change Checklist

A feature is not complete until every affected layer is updated. Before marking any task as done, verify this checklist:

| What changed | Must also update |
|---|---|
| **New plugin** | Plugin dir + Pydantic config + Zod schema + UI union index + UI form component + UI registry + MDX doc page + `meta.json` nav |
| **Plugin config field** | Pydantic model + Zod schema + UI form component + MDX docs |
| **Template context variable** | Template plugin + `globals.ts` autocomplete + `template.mdx` docs + content-packs `api-reference.md` |
| **Template module function** | `modules/<name>.py` + tests + `globals.ts` autocomplete + `template.mdx` docs + content-packs `api-reference.md` |
| **API route** | FastAPI router + re-export OpenAPI spec + `pnpm generate-api-docs` + UI API calls if applicable |
| **New formatter** | Output base plugin + Zod schemas + `FormatterParams.tsx` + `formatters.mdx` |
| **New release** | `eventum/__init__.py` version + CHANGELOG.md (git-cliff) + docs changelog MDX page + `meta.json` |

## Key Paths

- **Pydantic configs**: `eventum/plugins/<type>/plugins/<name>/config.py`
- **Zod schemas**: `eventum/ui/src/api/routes/generator-configs/schemas/plugins/<type>/configs/`
- **UI registry**: `eventum/ui/src/api/routes/generator-configs/modules/plugins/registry.ts`
- **UI forms**: `eventum/ui/src/pages/ProjectPage/<Type>PluginTab/<Type>PluginParams/`
- **Editor autocomplete**: `eventum/ui/src/pages/ProjectPage/common/EditorTab/FileEditor/completions/globals.ts`
- **OpenAPI spec**: `../docs/public/schemas/eventum-openapi.json`
- **MDX docs**: `../docs/content/docs/`
- **Content packs API ref**: `../content-packs/api-reference.md`

## Verification Commands

After any cross-cutting change, run the full pipeline:

```bash
uv run pytest                    # Python tests
uv run ruff check .              # Python lint
uv run mypy eventum/             # Python types
cd ../docs && pnpm build         # Docs build (catches broken MDX/nav)
```
