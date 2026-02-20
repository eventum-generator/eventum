#!/usr/bin/env bash
# Release script for Eventum
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 2.0.1

set -euo pipefail

# ── Args ────────────────────────────────────────────────────────────────────
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 2.0.1"
  exit 1
fi

TAG="v${VERSION}"
INIT_FILE="eventum/__init__.py"
DEVELOP_BRANCH="develop"
MASTER_BRANCH="master"

# ── Helpers ─────────────────────────────────────────────────────────────────
info()    { echo -e "\033[1;34m==> $1\033[0m"; }
success() { echo -e "\033[1;32m==> $1\033[0m"; }
error()   { echo -e "\033[1;31m==> $1\033[0m"; exit 1; }
confirm() {
  read -rp $'\033[1;33m'"==> $1 [y/N] "$'\033[0m' answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
}

# ── Preflight checks ───────────────────────────────────────────────────────
info "Releasing Eventum ${VERSION}"

# Ensure we're in the repo root
[[ -f "$INIT_FILE" ]] || error "Run this script from the repository root"

# Ensure working tree is clean
if [[ -n "$(git status --porcelain)" ]]; then
  error "Working tree is not clean. Commit or stash changes first."
fi

# Ensure we're on develop
CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$DEVELOP_BRANCH" ]]; then
  error "You must be on '${DEVELOP_BRANCH}' branch (currently on '${CURRENT_BRANCH}')"
fi

# Ensure tag doesn't already exist
if git rev-parse "$TAG" &>/dev/null; then
  error "Tag '${TAG}' already exists"
fi

# ── Step 1: Bump version ───────────────────────────────────────────────────
CURRENT_VERSION=$(python -c "import re; print(re.search(r\"__version__\s*=\s*['\"](.+?)['\"]\", open('${INIT_FILE}').read()).group(1))")
info "Current version: ${CURRENT_VERSION}"
info "New version:     ${VERSION}"

if [[ "$CURRENT_VERSION" == "$VERSION" ]]; then
  info "Version already set to ${VERSION}, skipping bump"
else
  confirm "Bump version from ${CURRENT_VERSION} to ${VERSION}?"
  sed -i "s/__version__ = '${CURRENT_VERSION}'/__version__ = '${VERSION}'/" "$INIT_FILE"
  success "Version bumped in ${INIT_FILE}"
fi

# ── Step 2: Run checks ─────────────────────────────────────────────────────
info "Running lint..."
uv run ruff check .

info "Running type check..."
uv run mypy eventum/

info "Running tests..."
uv run pytest

success "All checks passed"

# ── Step 3: Commit version bump ────────────────────────────────────────────
if [[ -n "$(git status --porcelain)" ]]; then
  confirm "Commit version bump?"
  git add "$INIT_FILE"
  git commit -m "chore: bump version to ${VERSION}"
  success "Version bump committed"
fi

# ── Step 4: Merge develop → master ─────────────────────────────────────────
confirm "Merge '${DEVELOP_BRANCH}' into '${MASTER_BRANCH}' and tag '${TAG}'?"

git checkout "$MASTER_BRANCH"
git pull origin "$MASTER_BRANCH"
git merge "$DEVELOP_BRANCH" --no-ff -m "release: ${VERSION}"
success "Merged ${DEVELOP_BRANCH} into ${MASTER_BRANCH}"

# ── Step 5: Tag ────────────────────────────────────────────────────────────
git tag -a "$TAG" -m "Release ${VERSION}"
success "Created tag ${TAG}"

# ── Step 6: Push ───────────────────────────────────────────────────────────
confirm "Push '${MASTER_BRANCH}' and tag '${TAG}' to origin? This will trigger the release pipeline."

git push origin "$MASTER_BRANCH"
git push origin "$TAG"
success "Pushed ${MASTER_BRANCH} and ${TAG}"

# ── Step 7: Back to develop ────────────────────────────────────────────────
git checkout "$DEVELOP_BRANCH"
git merge "$MASTER_BRANCH" --ff-only
success "Back on ${DEVELOP_BRANCH}"

echo ""
success "Release ${VERSION} complete!"
echo "  PyPI + Docker publish will run via GitHub Actions."
echo "  Monitor: https://github.com/eventum-project/eventum-generator/actions"
