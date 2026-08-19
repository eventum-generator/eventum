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

## Stance

An issue is the author's view at filing time, not a design. Verify its claims: the stated cause may be wrong, the proposed solution is one option, an "out of scope" note is a guess - what the feature cannot ship without belongs in this change. Cases the issue never mentions - error paths, boundaries, concurrency, existing data - still need an answer.

Disagreements go into the plan (step 2), never into a silently wider diff.

## Process

Eight steps. Step 2 requires user approval. Step 5 re-runs after fixes; step 6 reviews through independent subagents and sends work back to step 5. Side-improvements spotted along the way stay out of the diff (see Notes).

### 1. Understand

Fetch the issue with comments:

```bash
gh issue view <n> --json title,body,labels,assignees,milestone,comments
```

Later comments often narrow or redirect the original ask - resolve what "done" means before planning. If the issue is ambiguous, stale, or blocked by an upstream decision, surface it to the user before step 2.

Reproduce a reported bug before accepting the diagnosis - an actual failing run, not agreement with the issue text.

For unfamiliar areas, read the files the issue touches and the rules under `.claude/rules/**` that match those paths. Identify existing patterns before designing new ones.

### 2. Plan

Plan depth matches issue complexity. A single-cause bug: name the cause and the minimal patch. A feature or cross-cutting change: list files to create or modify, call out design choices and trade-offs. Tie every decision to a fact from the issue or the code.

Present the plan and wait for approval. It names where you disagree with the issue, what it left undecided, and what it excluded that the feature cannot ship without. Unrelated improvements stay out (see Notes).

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

### 6. Adversarial review

Self-review is the weakest check: the reasoning that wrote the defect clears it, and green tests read as proof. Dispatch four read-only subagents in parallel, one lens each, with the issue number, the worktree path, the base ref (`origin/develop`), and the rules matching touched paths.

- **Correctness** - inputs and states that break it: error paths, boundaries, concurrency, resource lifetimes.
- **Test integrity** - assume the tests prove nothing: what still passes after a regression, what is mocked away or asserted vacuously.
- **Contracts and rules** - `.claude/rules/**` and the cross-cutting sync they demand (Zod schema and form, `LOGGING.md` fields, OpenAPI export, docs).
- **Requirement fidelity** - issue and comments against the diff: what is missing, partial, or reinterpreted.

Each finding: claim, `file:line`, and a concrete failure scenario (inputs -> wrong result).

Verify every finding against the code before acting - a testable claim gets the failing test. Then fix it (return to step 5), refute it with evidence, or defer it as a follow-up issue. Blanket-accepting and blanket-dismissing are the same failure. Re-dispatch once if triage changed logic; after two rounds report what stays open.

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

- A scope gap breaks the feature the issue asked for and belongs in the plan (step 2); a side-improvement merely sits nearby and stays out of the diff.
- Side-improvements spotted during implementation: keep a one-line list and offer to file them as follow-up issues after the PR is open, through the `issue` skill. Do not expand the current diff.
- Merge, tag, and release belong to the `release` skill. Not current.
