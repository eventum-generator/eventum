---
name: new-plugin
description: Add a new input, event, or output plugin to the Eventum backend — code, config, tests, docs.
user-invocable: true
disable-model-invocation: true
argument-hint: "<type>/<name> (e.g. input/kafka, output/s3, event/jsonl)"
---

## Add New Plugin

Create a new Eventum plugin of the specified type and name: **$ARGUMENTS**.

Parse the argument as `<type>/<name>` where type is `input`, `event`, or `output`.

### Phase 1: Research

1. Study the existing plugins of the same type to understand patterns:
   - Read the base class: `eventum/plugins/<type>/base/plugin.py`
   - Read 1-2 existing plugin implementations in `eventum/plugins/<type>/plugins/`
   - Read the plugin config patterns: each plugin has `config.py` (Pydantic model) + `plugin.py` (implementation)
2. Read the plugin system docs: `eventum/plugins/registry.py` and `eventum/plugins/loader.py`
3. If the plugin integrates with an external system (e.g., Kafka, S3), research the best Python library for it.

### Phase 2: Plan

1. Enter plan mode and design the plugin:
   - Config model fields (with types, defaults, validation)
   - Plugin implementation approach
   - Test strategy
   - Any new dependencies needed
2. Reference the cross-cutting change checklist in CLAUDE.md to identify all affected layers.
3. Present the plan for approval.

### Phase 3: Implement

After approval, create the plugin following this structure:

```
eventum/plugins/<type>/plugins/<name>/
├── __init__.py      # empty
├── config.py        # Pydantic config model (frozen, extra='forbid')
├── plugin.py        # Plugin class extending base
└── tests/
    ├── __init__.py  # empty
    └── test_<name>.py
```

**Code conventions:**
- Config model: frozen Pydantic `BaseModel`, all fields typed, docstring on class
- Plugin class: `class <Name>Plugin(<Type>Plugin[<Name>Config, <Type>PluginParams])`
- Module path must be exactly `eventum.plugins.<type>.plugins.<name>.plugin` (auto-registration depends on this)
- Use `self.resolve_path()` for any file path fields (resolves relative to generator base path)
- Use `self.logger` for logging (pre-bound with plugin context)
- Explicit over clever — straightforward implementation

**Tests:**
- Co-located in the plugin's `tests/` directory
- Test config validation (valid + invalid inputs)
- Test core plugin behavior with mocked external dependencies
- Use `pytest` fixtures, `unittest.mock` for mocking

### Phase 4: Update UI (if applicable)

If this is a new plugin, update the Eventum Studio UI:

1. **Zod schema**: Create `eventum/ui/src/api/routes/generator-configs/schemas/plugins/<type>/configs/<name>/index.ts`
   - Mirror the Pydantic config model exactly
   - Use `orPlaceholder()` wrapper from `schemas/placeholder.ts` for fields that support `${params.*}` / `${secrets.*}`
2. **Plugin union**: Add the new plugin to `eventum/ui/src/api/routes/generator-configs/schemas/plugins/<type>/index.ts`
3. **UI form**: Create form component in `eventum/ui/src/pages/ProjectPage/<Type>PluginTab/<Type>PluginParams/`

Ask the user whether to implement UI changes or skip for now.

### Phase 5: Documentation

Create the docs page at `../docs/content/docs/plugins/<type>/<name>.mdx`:

- Frontmatter: title, description, icon (from Lucide)
- Overview: what the plugin does, when to use it
- Configuration: full parameter table with types, defaults, descriptions
- Examples: at least 2 `generator.yml` snippets (basic + advanced)
- Input→output example showing what the plugin produces
- Add entry to `../docs/content/docs/plugins/<type>/meta.json`

### Phase 6: Update CLAUDE.md

Update CLAUDE.md files to reflect the new plugin:

1. **`CLAUDE.md`** (this repo) — Update plugin tables and counts. If the plugin adds a new dependency, update the Python dependencies section. Reference the "Keeping CLAUDE.md Accurate" section for the full list of triggers.
2. **`../docs/CLAUDE.md`** — Add the new plugin docs page to the **Content Structure** tree under `plugins/<type>/`.

### Phase 7: Verify

Run full verification pipeline:

```bash
uv run pytest eventum/plugins/<type>/plugins/<name>/tests/ -v
uv run ruff check eventum/plugins/<type>/plugins/<name>/
uv run mypy eventum/plugins/<type>/plugins/<name>/
cd ../docs && pnpm build
```

### Important

- Do NOT commit or push unless the user explicitly asks.
- Track progress with the todo list throughout.
- If blocked or uncertain, ask the user rather than guessing.
- Check CLAUDE.md cross-cutting change checklist for completeness.
