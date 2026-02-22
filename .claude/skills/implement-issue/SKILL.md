---
name: implement-issue
description: Implement a GitHub issue end-to-end — plan, code, test, document, verify, close.
user-invocable: true
disable-model-invocation: true
argument-hint: "#<issue-number>"
---

## Implement GitHub Issue

Implement the GitHub issue **$ARGUMENTS** in the `eventum-generator/eventum` repository, following the full lifecycle below.

### Phase 1: Understand

1. Fetch the issue details: `gh issue view <number> --json title,body,labels,assignees,milestone,projectItems`
2. Read and understand the issue requirements thoroughly.
3. Check the issues comments and understand intentions of participants.
4. Explore the relevant parts of the codebase to understand existing patterns, conventions, and where changes are needed.

### Phase 2: Plan

1. Enter plan mode and design an implementation approach.
2. Identify all files that need to be created or modified (code, tests, docs).
3. Present the plan to the user for approval before writing any code.

### Phase 3: Implement

After plan approval, execute the changes:

1. **Code** — Make the implementation changes in the `eventum` Python package. Follow existing conventions:
   - Style: Ruff with ALL rules, single quotes, 79-char lines.
   - Types: Full type annotations, Pydantic models where appropriate.
   - Keep changes minimal and focused on the issue requirements.
   - **Performance**: Optimize for high throughput — this codebase processes up to 1M+ events/sec. Cache computed values, pre-build objects at init time, minimize per-call allocations, use O(1) lookups over linear scans. Sacrifice verbose error details on hot paths if needed; validate lazily (once on first use, then cached).
   - **Maintainability**: Write clean, well-structured code that is easy to read and extend. Use clear naming, consistent patterns, and logical organization. Code should be self-documenting with concise docstrings on public APIs.
   - **Architecture**: Design extensible, composable abstractions. Prefer proper classes over ad-hoc structures. Keep responsibilities separated and interfaces minimal.

2. **Tests** — Add or update tests. Tests are co-located: `<package>/tests/test_<name>.py`. Follow the existing test style in the file being modified.

3. **Documentation** — If the change affects user-facing behavior, update the relevant docs in `../docs/content/docs/`. Match existing MDX formatting (tables, code blocks, callouts).

### Phase 4: Verify

Run all relevant checks and fix any failures:

```
uv run pytest <relevant-test-file> -v          # Tests pass
uv run ruff check <changed-files>              # Lint clean
uv run mypy <changed-source-files>             # Types clean
```

If documentation was updated, also verify the docs site builds:
```
cd ../docs && pnpm build                       # Docs build clean
```

### Phase 5: Close

0. Ask user whether we close the issue first.
1. **Comment on the issue** with a summary of changes:
   - What was added/changed (brief)
   - Which files were modified
   - Usage example (if applicable)
2. **Close the issue**: `gh issue close <number> --reason completed`
3. Verify the issue moved to "Done" in the project board: `gh issue view <number> --json state,projectItems`

### Important

- Do NOT commit or push unless the user explicitly asks.
- Do NOT create files that aren't necessary — prefer editing existing files.
- Track progress with the todo list throughout.
- If blocked or uncertain, ask the user rather than guessing.
