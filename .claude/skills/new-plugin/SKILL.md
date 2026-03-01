---
name: new-plugin
description: Add a new input, event, or output plugin to Eventum -- orchestrate agents through research, design, code, UI, review, docs.
user-invokable: true
argument-hint: "<type>/<name> (e.g. input/kafka, output/s3, event/jsonl)"
---

## Add New Plugin

Orchestrate the creation of a new Eventum plugin **$ARGUMENTS** by delegating to your team of agents.

Parse the argument as `<type>/<name>` where type is `input`, `event`, or `output`.

### Phase 1: Research

**Delegate to researcher agent**:

- Study existing plugins of the same type: read base classes, config patterns, test structure
- Research the external technology (library, protocol, API) the plugin will integrate with
- Identify dependencies, authentication patterns, configuration options
- Report findings with recommendations

### Phase 2: Design

**Delegate to architect agent**:

- Design the plugin based on researcher's findings: config model, implementation approach, test strategy
- Follow plugin conventions: Pydantic config (frozen, `extra='forbid'`), class extending base plugin
- Plan the UI integration (Zod schema, form component)
- Produce implementation plan with ordered steps

**TL directly**: Present the design to the user for approval. Ask whether to implement UI changes or skip for now.

### Phase 3: Implement

**Delegate to developer agent**:

- Create plugin directory: `eventum/plugins/<type>/plugins/<name>/`
  - `config.py` -- Pydantic config model
  - `plugin.py` -- Plugin class extending the base
  - `__init__.py` -- Exports
  - `tests/` -- Test directory structure
- If UI approved:
  - Zod schema mirroring the Pydantic config
  - UI form component
  - Registry entries (union index, default config, plugin info)
- Run ruff/mypy on own code before returning

**Checkpoint**: Present the developer's changes to the user before proceeding.

### Phase 4: Test

**Delegate to qa-engineer agent**:

- Write comprehensive tests in `eventum/plugins/<type>/plugins/<name>/tests/`
- Test plugin functionality, config validation, edge cases, error paths
- Run: `uv run pytest eventum/plugins/<type>/plugins/<name>/tests/ -v`
- Run: `uv run ruff check` and `uv run mypy` on all changed files
- Report results

If QA reports failures: route findings to **developer** to fix, then re-run QA. Loop until all checks pass.

### Phase 5: Code Review

**Delegate to code-reviewer agent**:

- Review ALL changes: Python plugin code + UI code (if any) + tests
- If verdict is **FAIL**: route findings to **developer** and/or **qa-engineer** to fix, then re-review
- Loop until **PASS**

This is a mandatory quality gate -- do NOT skip it.

### Phase 6: Documentation

**Delegate to docs-writer agent**:

- Create MDX page at `../docs/content/docs/plugins/<type>/<name>.mdx`:
  - Overview, configuration table, examples (basic + advanced), input/output example
- Add entry to `../docs/content/docs/plugins/<type>/meta.json`
- Add changelog entry to `CHANGELOG.md` under `## Unreleased` / `### New Features`

### Phase 7: Update CLAUDE.md

**Delegate to developer agent**:

- Update `CLAUDE.md` (this repo): plugin tables, counts, new dependency if applicable

### Phase 8: Final Verification

**Delegate to qa-engineer agent**:

- Run full pipeline:
  ```bash
  uv run pytest eventum/plugins/<type>/plugins/<name>/tests/ -v
  uv run ruff check eventum/plugins/<type>/plugins/<name>/
  uv run mypy eventum/plugins/<type>/plugins/<name>/
  cd ../docs && pnpm build
  ```
- Report all-green status

If any check fails: route to the responsible agent (**developer** for code, **docs-writer** for docs), fix, and re-verify.

### Phase 9: Summary

**TL directly**:

Present to the user:
- What was created (plugin code, UI, tests, docs)
- File list with key changes
- Verification results

### Important

- Do NOT commit or push unless the user explicitly asks.
- Track progress with the todo list throughout.
- If blocked or uncertain, ask the user rather than guessing.
- Check CLAUDE.md cross-cutting change checklist for completeness.
