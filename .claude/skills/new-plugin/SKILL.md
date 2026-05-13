---
name: new-plugin
description: Add a new input, event, or output plugin to Eventum - research, plan, branch, implement, verify, review, document, finalize.
---

## Input

- Plugin type (`input`, `event`, or `output`) and plugin name, e.g. a Kafka input plugin.
- Optional notes on the external technology (library, protocol, API) the plugin integrates with.

## Output

- Feature branch with plugin code, tests, UI, docs page, and changelog entry.
- PR opened against `develop`.

## Reference

- Plugin rules: `.claude/rules/backend/plugins.md` plus the type-specific file under `.claude/rules/backend/plugins/{input,event,output}.md`.
- UI rules: `.claude/rules/frontend/ui.md`, section "Plugin UI".
- Docs rules: `.claude/rules/docs/mdx.md`.
- Sibling plugins of the same type under `eventum/plugins/<type>/plugins/` - for layout and tone only.

## When to use

Any new input, event, or output plugin.

Not for: single-field additions to an existing plugin (handle inline); new formatters (separate checklist in `.claude/rules/backend/plugins/output.md`).

## Process

Eight steps. Step 2 requires user approval. Step 5 re-runs after fixes; step 6 sends work back to step 5. Step 8 waits on an explicit ask.

### 1. Research

Three inputs before planning:

- One or two sibling plugins of the same type, read closely for class shape, config shape, and test structure.
- The external technology - library choice, authentication, configuration options, error model.
- The plugin rules and the type-specific rules file for the chosen type.

### 2. Plan

The plan covers both surfaces:

- **Python** - config model (fields, validation, defaults), plugin class responsibilities, tests, new dependencies.
- **UI** - per `.claude/rules/frontend/ui.md`. Required by `.claude/rules/backend/plugins.md` and included by default; drop only on the user's explicit ask.

Tie each decision to a fact from research. Present the plan and wait for approval.

### 3. Branch

Create the feature branch (git-flow, off `develop`):

```bash
git switch develop && git pull
git switch -c feat/<short-slug>
```

### 4. Implement

Write code and tests together; every new control-flow branch and error path gets a test. Follow `.claude/rules/backend/plugins.md` (plus the type-specific file) and `.claude/rules/frontend/ui.md`. Keep the diff scoped to the plan.

### 5. Verify

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy eventum/
uv run pytest
cd eventum/ui && pnpm build
```

All green is required to advance. On failure, fix and re-run; if three cycles do not converge, stop and surface to the user.

### 6. Review

Review the full diff as a unit - Python, UI, and tests. Re-check the plugin and UI rules. Typical gaps: config field mismatch between Pydantic and Zod, untested error paths, violated plugin contract (wrong base class, wrong exception types).

Fix findings, return to step 5, and advance only when the review is clean.

### 7. Document

Three artifacts:

- MDX page under `../docs/content/docs/plugins/<type>/<name>.mdx`. Delegate to the `new-docs-page` skill rather than drafting inline; that skill runs the docs build.
- Row in the overview table for the plugin's type at `../docs/content/docs/plugins/index.mdx`.
- `CHANGELOG.md` entry. If `## Unreleased` is absent, create it above the latest version section; match the formatting of existing sections.

### 8. Finalize

On user approval (commits and pushes require an explicit ask):

1. Commit using conventional commits (scope: `plugins`).
2. Push the branch and open a PR targeting `develop` linking the work in the body.
3. Report the PR URL.

## Notes

- Side-improvements spotted during implementation: keep a one-line list and offer to file them as follow-up issues after the PR is open. Do not expand the current diff.
- Merge, tag, and release belong to the `release` skill.
