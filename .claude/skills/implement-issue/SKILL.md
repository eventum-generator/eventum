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
3. Check the issue comments and understand intentions of participants.
4. Explore the relevant parts of the codebase to understand existing patterns, conventions, and where changes are needed.

### Phase 2: Plan

1. Enter plan mode and design an implementation approach.
2. Identify all files that need to be created or modified (code, tests, docs).
3. Consult the **cross-cutting change checklist** in CLAUDE.md to ensure all affected layers are covered.
4. Present the plan to the user for approval before writing any code.

### Phase 3: Implement

After plan approval, execute the changes:

1. **Code** — Make the implementation changes in the `eventum` Python package. Follow existing conventions:
   - Style: Ruff with ALL rules, single quotes, 79-char lines.
   - Types: Full type annotations, Pydantic models where appropriate.
   - Keep changes minimal and focused on the issue requirements.
   - **Explicit over clever** — straightforward code that anyone can understand immediately. Avoid magic, metaprogramming, or complex patterns.
   - **SOLID + composition** — single responsibility, dependency injection, composition over inheritance. Extensible, composable abstractions.
   - **Performance** — optimize obvious bottlenecks but keep code readable. Pre-compute at init, cache computed values, minimize per-call allocations. Profile before hand-optimizing.
   - **Docstrings** — public API only, NumPy-style (Parameters/Returns/Raises). No inline comments unless truly non-obvious.
   - **Fix trivial issues** — fix obvious problems (typos, dead imports, clear bugs) near the code you're changing.

2. **Tests** — Every feature/fix must have tests. Tests are part of "done", no exceptions.
   - Co-located: `<package>/tests/test_<name>.py`
   - Follow the existing test style in the file being modified.
   - Test core logic, edge cases, and error paths.

3. **Documentation** — Feature isn't done until docs are updated (same session).
   - If the change affects user-facing behavior, update the relevant docs in `../docs/content/docs/`.
   - Match existing MDX formatting (tables, code blocks, callouts).
   - Use approachable guide style with input→output examples.

4. **CLAUDE.md** — If the change adds/removes plugins, changes architecture, bumps version, or adds CLI options, update the relevant CLAUDE.md files (see "Keeping CLAUDE.md Accurate" section).

**Checkpoint**: After implementing code, check in with the user before proceeding to tests and docs.

### Phase 4: Verify

Run the full verification pipeline and fix any failures:

```bash
uv run pytest <relevant-test-file> -v          # Tests pass
uv run ruff check <changed-files>              # Lint clean
uv run mypy <changed-source-files>             # Types clean
```

If documentation was updated, also verify the docs site builds:
```bash
cd ../docs && pnpm build                       # Docs build clean
```

### Phase 5: Improvements

If you discovered non-trivial improvements during implementation, create GitHub issues:
```bash
gh issue create --repo eventum-generator/eventum --title "<concise title>" --body "<problem + proposed solution>"
```
Check existing issues first to avoid duplicates.

### Phase 6: Close

1. Ask user whether to close the issue.
2. **Comment on the issue** with a summary of changes:
   - What was added/changed (brief)
   - Which files were modified
   - Usage example (if applicable)
3. **Close the issue**: `gh issue close <number> --reason completed`
4. Verify the issue state: `gh issue view <number> --json state,projectItems`

### Important

- Do NOT commit or push unless the user explicitly asks. When committing, use conventional commits: `feat(scope):`, `fix(scope):`, etc.
- Do NOT create files that aren't necessary — prefer editing existing files.
- Track progress with the todo list throughout.
- If blocked or uncertain, ask the user rather than guessing.
