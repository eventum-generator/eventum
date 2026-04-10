---
name: release
description: Prepare and execute an Eventum release - orchestrate agents through changelog, version bump, verification, PR, tag.
user-invokable: true
argument-hint: "<version> (e.g. 2.0.3)"
context: fork
---

## Current state
- Current version: !`grep -m1 '__version__' eventum/__init__.py`
- Unreleased changes: !`git log $(git describe --tags --abbrev=0)..HEAD --oneline`
- Branch status: !`git status --short`
- CI status: !`gh run list --limit 3`

## Release Eventum

Orchestrate the release for version **$ARGUMENTS** by delegating to your team of agents.

Parse the argument as the version number (e.g., `2.0.3`). If not provided, ask the user.

### Phase 1: Pre-flight Checks

**TL directly**:

1. Verify we're on the `develop` branch with a clean working tree:
   ```bash
   git branch --show-current
   git status --porcelain
   ```
2. Check the current version in `eventum/__init__.py`.
3. Verify the tag `v<version>` doesn't already exist.
4. Ask the user to confirm the version bump.

### Phase 2: Changelog

**Delegate to docs-writer agent**:

1. Finalize `CHANGELOG.md`:
   - If `## Unreleased` exists: rename to `## <version> (<date>)` (YYYY-MM-DD format)
   - Cross-check with commits since last tag:
     ```bash
     git tag --list 'v*' --sort=-version:refname | head -5
     git log <latest-tag>..HEAD --format='%H %s%n%b---'
     ```
   - Add any missing entries, clean up wording
   - If `## Unreleased` doesn't exist: create version entry from git history
2. Create docs changelog page at `../docs/content/docs/changelog/<version>.mdx`
3. Update `../docs/content/docs/changelog/meta.json` with the new page

### Phase 3: Version Bump

**Delegate to developer agent**:

1. Update `eventum/__init__.py`: `__version__ = '<version>'`
2. Update CLAUDE.md files to reflect the new version

### Phase 4: Verification

**Delegate to qa-engineer agent**:

- Run the complete check suite:
  ```bash
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy eventum/
  uv run pytest
  cd ../docs && pnpm build
  ```
- Report results

If any check fails: route to the responsible agent (**developer** for code, **docs-writer** for docs), fix, and re-verify. If the loop does not converge after 3 cycles, stop and consult the user.

### Phase 5: Present Summary

**TL directly**:

Show the user a summary of all changes:
- Version bump diff
- Changelog entries (both files)
- Full check results
- What happens next (commit, push, PR, merge, tag)

Ask the user to review before committing.

### Phase 6: Commit & PR (on user approval)

**TL directly**:

1. Commit all changes: `chore: bump version to <version>`
2. Push to `develop`.
3. Create the release PR:
   ```bash
   gh pr create --base master --head develop --title "Release <version>" --body "..."
   ```
4. Report the PR URL.

### Phase 7: Tag (after PR merge)

**TL directly** (after user confirms PR was merged):

1. Fetch and checkout `master`.
2. Verify the version matches.
3. Create annotated tag: `git tag -a v<version> -m "Release <version>"`
4. Push the tag: `git push origin v<version>`
5. Switch back to `develop`.

The tag push triggers the CI release pipeline (PyPI + Docker Hub).

### Phase 8: GitHub Release

**TL directly**:

```bash
gh release create v<version> --title "Eventum <version>" --notes "..."
```

Use the same content as the docs changelog MDX. Include a full changelog link:
```
**Full Changelog**: https://github.com/eventum-generator/eventum/compare/v<previous-version>...v<version>
```

### Phase 9: Announcement Discussion

**TL directly**:

Create a discussion in the Announcements category via GraphQL:

```bash
gh api graphql -f query='
mutation {
  createDiscussion(input: {
    repositoryId: "<repo-node-id>",
    categoryId: "DIC_kwDOKpjxBc4CfS4C",
    title: "Eventum <version> Released",
    body: "..."
  }) {
    discussion { url }
  }
}'
```

- Get repo node ID: `gh api graphql -f query='{ repository(owner: "eventum-generator", name: "eventum") { id } }'`
- Announcements category ID: `DIC_kwDOKpjxBc4CfS4C`

### Phase 10: Promotion (Optional)

**TL directly**:

Ask the user: "Would you like to create additional promotional content for this release?"

If yes, **delegate to content-growth agent**:

- Draft blog post for the docs site (`../docs/content/blog/`)
- Draft social media posts for relevant platforms (Reddit, Twitter/X, LinkedIn, Habr)
- Suggest external platforms for cross-posting with reasoning

Present drafts to the user for review and publishing.

### Important

- Each phase requires user confirmation before proceeding to the next.
- Do NOT force-push or run destructive git operations.
- Track progress with the todo list throughout.
