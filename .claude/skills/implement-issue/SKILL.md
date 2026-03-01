---
name: implement-issue
description: Implement a GitHub issue end-to-end -- orchestrate agents through plan, code, test, review, document, verify, close.
user-invokable: true
argument-hint: "#<issue-number>"
---

## Implement GitHub Issue

Orchestrate the implementation of GitHub issue **$ARGUMENTS** by delegating to your team of agents.

### Phase 1: Understand

**TL directly**:

1. Fetch the issue details: `gh issue view <number> --json title,body,labels,assignees,milestone,projectItems`
2. Read the issue comments to understand intentions of participants.

**Delegate to researcher agent** (optional -- use for complex issues or unfamiliar areas):

- Explore the relevant parts of the codebase
- Identify existing patterns, conventions, and where changes are needed
- Report findings

### Phase 2: Design

**Delegate to architect agent** (skip for simple bug fixes):

- Design an implementation approach based on issue requirements and researcher findings
- Identify all files that need to be created or modified
- Consult the cross-cutting change checklist in CLAUDE.md
- Produce 2-3 options with recommendation

**TL directly**: Present the plan to the user for approval before proceeding.

### Phase 3: Implement

**Delegate to developer agent**:

- Implement all code changes (Python backend + React/TS frontend if needed)
- Follow the architect's design if one exists
- Run ruff/mypy on own code before returning

**Checkpoint**: Present the developer's changes to the user before proceeding.

### Phase 4: Test

**Delegate to qa-engineer agent**:

- Write tests for all new functionality (co-located in `<package>/tests/test_<name>.py`)
- Run full verification pipeline: pytest + ruff + mypy
- Report results

If QA reports failures: route findings to **developer** to fix, then re-run QA. Loop until all checks pass.

### Phase 5: Code Review

**Delegate to code-reviewer agent**:

- Review ALL changes as a unit: implementation code + tests
- If verdict is **FAIL**: route findings to **developer** and/or **qa-engineer** to fix, then re-review
- Loop until **PASS**

This is a mandatory quality gate -- do NOT skip it.

### Phase 6: Documentation

**Delegate to docs-writer agent** (if change affects user-facing behavior):

- Update relevant docs in `../docs/content/docs/`
- Add changelog entry to `CHANGELOG.md` under `## Unreleased`

### Phase 7: Final Verification

**Delegate to qa-engineer agent**:

- Run the full pipeline: pytest + ruff + mypy
- If docs were changed: `cd ../docs && pnpm build`
- Report all-green status

If any check fails: route to the responsible agent (**developer** for code, **docs-writer** for docs), fix, and re-verify.

### Phase 8: Improvements

**TL directly**:

If non-trivial improvements were discovered during implementation, create GitHub issues:
```bash
gh issue create --repo eventum-generator/eventum --title "<title>" --body "<problem + proposed solution>"
```
Check existing issues first to avoid duplicates.

### Phase 9: Close

**TL directly**:

1. Ask user whether to close the issue.
2. Comment on the issue with a summary of changes (what changed, which files, usage example).
3. Close: `gh issue close <number> --reason completed`

### Important

- Do NOT commit or push unless the user explicitly asks. Use conventional commits: `feat(scope):`, `fix(scope):`, etc.
- Track progress with the todo list throughout.
- If blocked or uncertain, ask the user rather than guessing.
