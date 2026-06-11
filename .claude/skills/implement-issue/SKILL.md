---
name: implement-issue
description: Implement a GitHub issue end-to-end - understand, plan, branch, implement with tests, verify, review, document, finalize.
---

## Input

- GitHub issue number in `eventum-generator/eventum`.

## Output

- Feature branch with implementation, tests, and (when user-facing) docs and a changelog entry.
- PR opened against `develop`.

## Reference

Rules under `.claude/rules/**` - consult the ones matching touched paths.

## When to use

Any issue beyond a one-line typo or comment fix. A trivial edit can skip straight to a commit.

## Process

Eight steps. Step 2 requires user approval. Step 5 re-runs after fixes; step 6 sends work back to step 5. Side-improvements spotted along the way stay out of the diff (see Notes).

### 1. Understand

Fetch the issue with comments:

```bash
gh issue view <n> --json title,body,labels,assignees,milestone,comments
```

Later comments often narrow or redirect the original ask - resolve what "done" means before planning. If the issue is ambiguous, stale, or blocked by an upstream decision, surface it to the user before step 2.

For unfamiliar areas, read the files the issue touches and the rules under `.claude/rules/**` that match those paths. Identify existing patterns before designing new ones.

### 2. Plan

Plan depth matches issue complexity. A single-cause bug: name the cause and the minimal patch. A feature or cross-cutting change: list files to create or modify, call out design choices and trade-offs. Tie every decision to a fact from the issue or the code.

Present the plan and wait for approval. Do not widen scope beyond what the issue defines.

### 3. Branch

Work happens in an isolated git worktree - several agents may run in parallel on the same repo, so the main checkout cannot be touched. Create the worktree off the current `develop` (fetch first to pick up new commits):

```bash
git fetch origin develop
git worktree add -b feat/<short-slug> .claude/worktrees/<short-slug> origin/develop
cd .claude/worktrees/<short-slug>
git branch --unset-upstream
```

The `--unset-upstream` is mandatory - basing on `origin/develop` makes git treat develop as the tracked branch, which would route a later `git push` to develop. Clear it now so the first `git push -u origin feat/<short-slug>` sets the correct upstream.

Stay in that worktree for all subsequent steps. Skip if the worktree for this issue already exists - just `cd` into it.

### 4. Implement

Write code and tests together; every new control-flow branch and error path gets a test. Follow path-local rules under `.claude/rules/**` and the style. Keep the diff scoped to the issue.

### 5. Verify

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy eventum/
uv run pytest
```

If the UI changed:

```bash
cd eventum/ui && pnpm build
```

All green is required to advance. On failure, fix and re-run; if three cycles do not converge, stop and surface to the user.

### 6. Review

Review the full diff as a unit - implementation, tests, docs if present. Re-check rules and style. Typical gaps: scope creep, untested branches, violated plugin or API contracts, style drift. Fix findings, return to step 5, and advance only when the review is clean.

### 7. Document

Only when the change is user-facing. Skip for internal refactors, test-only changes, and build plumbing.

- Update docs under `../docs/content/docs/` matching the touched area. When the feature has no existing page, delegate to the `new-docs-page` skill rather than drafting one inline.
- Add an entry to `CHANGELOG.md`. If `## Unreleased` is absent, create it above the latest version section; match the formatting of existing sections.

After inline edits, verify the docs site still builds:

```bash
cd ../docs && pnpm build
```

Skip this check when the work was delegated to `new-docs-page` - that skill runs the build itself.

### 8. Finalize

On user approval (commits and pushes require an explicit ask):

1. Commit using conventional commits.
2. Push the branch with `git push -u origin feat/<short-slug>` and open a PR targeting `develop` with referencing original issue in the body.
3. Report the PR URL. User will close PR and issue manually.
4. Worktree stays in `.claude/worktrees/<short-slug>` for follow-up review fixes. Remove it only on the user's explicit ask: `git worktree remove .claude/worktrees/<short-slug>` from the main checkout.

## Notes

- Side-improvements spotted during implementation: keep a one-line list and offer to file them as follow-up issues after the PR is open. Do not expand the current diff.
- Merge, tag, and release belong to the `release` skill. Not current.
