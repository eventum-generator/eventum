---
name: release
description: Prepare and execute an Eventum release — version bump, changelog, checks, PR, tag.
user-invocable: true
disable-model-invocation: true
argument-hint: "<version> (e.g. 2.0.3)"
---

## Release Eventum

Prepare and execute the release for version **$ARGUMENTS**.

Parse the argument as the version number (e.g., `2.0.3`). If not provided, ask the user.

### Phase 1: Pre-flight Checks

1. Verify we're on the `develop` branch with a clean working tree:
   ```bash
   git branch --show-current
   git status --porcelain
   ```
2. Check the current version in `eventum/__init__.py`.
3. Verify the tag `v<version>` doesn't already exist.
4. Ask the user to confirm the version bump.

### Phase 2: Changelog

Before bumping, generate the changelog from git history:

1. Find the latest release tag:
   ```bash
   git tag --list 'v*' --sort=-version:refname | head -5
   ```
2. Analyze commits since last tag:
   ```bash
   git log <latest-tag>..HEAD --format='%H %s%n%b---'
   git diff <latest-tag>..HEAD --stat
   ```
3. Update `CHANGELOG.md` — prepend new version entry above the previous one. Use the established format (read existing entries for reference). Categorize: features, bug fixes, performance, testing, architecture, other.
4. Create docs changelog page at `../docs/content/docs/changelog/<version>.mdx` — user-facing, slightly more general than CHANGELOG.md. Use the format from existing changelog MDX files.

### Phase 3: Version Bump

1. Update `eventum/__init__.py`:
   ```python
   __version__ = '<version>'
   ```

### Phase 4: Update CLAUDE.md

Update CLAUDE.md files to reflect the new version:

1. **`CLAUDE.md`** (this repo) — Update the version number wherever it appears (overview text, package structure tree). Reference the "Keeping CLAUDE.md Accurate" section for the full list of triggers.
2. **`../docs/CLAUDE.md`** — Add the new changelog version to the **Content Structure** tree under `changelog/`.

### Phase 5: Full Verification

Run the complete check suite:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy eventum/
uv run pytest
cd ../docs && pnpm build
```

Fix any failures before proceeding.

### Phase 6: Present Summary

Show the user a summary of all changes:
- Version bump diff
- Changelog entries (both files)
- Full check results
- What happens next (commit, push, PR, merge, tag)

Ask the user to review before committing.

### Phase 7: Commit & PR (on user approval)

1. Commit all changes:
   ```
   chore: bump version to <version>
   ```
2. Push to `develop`.
3. Create the release PR via `gh`:
   ```bash
   gh pr create --base master --head develop --title "Release <version>" --body "..."
   ```
4. Report the PR URL.

### Phase 8: Tag (after PR merge)

After the user confirms the PR was merged:

1. Fetch and checkout `master`.
2. Verify the version matches.
3. Create annotated tag: `git tag -a v<version> -m "Release <version>"`
4. Push the tag: `git push origin v<version>`
5. Switch back to `develop`.

The tag push triggers the CI release pipeline (PyPI + Docker Hub).

### Important

- Each phase requires user confirmation before proceeding to the next.
- Do NOT force-push or run destructive git operations.
- The release script at `scripts/release.sh` handles the same flow interactively — this skill provides a guided alternative.
- Track progress with the todo list throughout.
