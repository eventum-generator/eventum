---
name: release
description: Prepare and execute an Eventum release - changelog, version bump, verification, PR, tag, GitHub release, announcement.
---

## Input

- Version number (e.g. `2.0.3`).

## Output

- Two PRs merged by the user: `eventum` (`develop` -> `master`) and `../docs` (`release/<version>` -> `master`).
- Tag `v<version>` on `eventum` `master`, pushed only after both PRs merge.
- PyPI package and Docker Hub image (published by CI on tag push).
- GitHub release with notes and a full changelog link.
- Announcement discussion in the Announcements category.

## Reference

- `CHANGELOG.md` - existing version sections set the formatting convention.
- Last release tags and PRs - tone for release notes and announcement body.

## When to use

Cutting a new versioned release of `eventum` (PyPI package + Docker image).

Not for: docs-only updates, content-pack changes (independent flow under `../content-packs/`).

## Process

Seven steps. Steps 1, 5, and 7 are user checkpoints. Step 4 sends work back to step 2 or 3 on failure.

### 1. Pre-flight

Verify the release environment:

- Branch is `develop` with a clean working tree.
- Read the current `__version__` from `eventum/__init__.py`. Confirm the requested `<version>` is greater than it, and keep the current value as `<previous>` for step 7's full-changelog link.
- Tag `v<version>` does not exist (`git tag --list 'v<version>'`).

Confirm the version bump with the user before continuing.

### 2. Changelog

Two artifacts across two repos, each in its own voice:

- `eventum` on `develop` - rename `## Unreleased` in `CHANGELOG.md` to `## <version> (<date>)` in YYYY-MM-DD form. When no `Unreleased` section exists, build the section from `git log <latest-tag>..HEAD`. Always re-check the resulting list against `git log <latest-tag>..HEAD` even when an `Unreleased` section was already present - small fixes often land without a CHANGELOG entry. Fill gaps, polish wording. Technical voice, for developers.
- `../docs` - new page at `content/docs/changelog/<version>.mdx`, registered in `content/docs/changelog/meta.json`. User-facing voice: describe what changed for the end user (not developer) - not a one-to-one copy of the CHANGELOG entry. Commits land on a dedicated branch in step 6.

### 3. Version bump

- `eventum/__init__.py`: `__version__ = '<version>'`.

### 4. Verify

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy eventum/
uv run pytest
cd ../docs && pnpm build
```

All green is required to advance. On failure, fix in step 2 or 3 and re-run; if three cycles do not converge, stop and surface to the user.

### 5. Approve

Show the user:

- Version bump diff.
- Changelog entries (CHANGELOG.md + docs MDX).
- Verification results.
- What happens next: commits, push, two PRs, user merges both, tag, GitHub release, announcement.

Wait for explicit go-ahead before proceeding.

### 6. Open PRs

Two PRs, both targeting `master`:

In `eventum`:

```bash
git add -A && git commit -m "chore: bump version to <version>"
git push origin develop
gh pr create --base master --head develop --title "Release <version>"
```

In `../docs` (branch off `master`):

```bash
git switch master && git pull
git switch -c release/<version>
git add -A && git commit -m "docs: changelog for <version>"
git push -u origin release/<version>
gh pr create --base master --head release/<version> --title "docs: changelog for <version>"
```

Report both PR URLs.

### 7. Tag and publish

After the user confirms both PRs were merged:

1. In `eventum`: fetch and switch to `master`, verify the version bump landed.
2. Annotated tag and push - CI pipeline takes over from here (PyPI + Docker Hub).
3. Switch back to `develop`.
4. Create the GitHub release with notes mirroring the docs changelog MDX, plus a full changelog link.
5. Open an announcement discussion in the Announcements category.

Tag:

```bash
git tag -a v<version> -m "Release <version>"
git push origin v<version>
```

GitHub release:

```bash
gh release create v<version> --title "Eventum <version>" --notes "..."
```

Full changelog link to append to the release notes:

```
**Full Changelog**: https://github.com/eventum-generator/eventum/compare/v<previous>...v<version>
```

Announcement discussion (Announcements category ID `DIC_kwDOKpjxBc4CfS4C`):

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

Repo node ID is stable across releases - fetch once:

```bash
gh api graphql -f query='{ repository(owner: "eventum-generator", name: "eventum") { id } }'
```

## Notes

- Never force-push or run destructive git operations.
