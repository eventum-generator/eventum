#!/usr/bin/env bash
# Release script for Eventum
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 2.0.1
#
# Flow:
#   1. Bump version on develop
#   2. Run local checks (lint, types, tests)
#   3. Commit & push develop
#   4. Create PR develop → master via GitHub CLI
#   5. After PR is merged, tag master and push tag to trigger release pipeline

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

# Ensure gh CLI is available
command -v gh &>/dev/null || error "'gh' CLI is required. Install: https://cli.github.com"

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

# ── Step 3: Commit & push ──────────────────────────────────────────────────
if [[ -n "$(git status --porcelain)" ]]; then
  confirm "Commit version bump and push to origin/${DEVELOP_BRANCH}?"
  git add "$INIT_FILE"
  git commit -m "chore: bump version to ${VERSION}"
  success "Version bump committed"
fi

git push origin "$DEVELOP_BRANCH"
success "Pushed ${DEVELOP_BRANCH}"

# ── Step 4: Create pull request ─────────────────────────────────────────────
confirm "Create release PR: ${DEVELOP_BRANCH} → ${MASTER_BRANCH}?"

PR_URL=$(gh pr create \
  --base "$MASTER_BRANCH" \
  --head "$DEVELOP_BRANCH" \
  --title "Release ${VERSION}" \
  --body "$(cat <<EOF
## Release ${VERSION}

Merge \`${DEVELOP_BRANCH}\` into \`${MASTER_BRANCH}\` for release ${TAG}.

After merging, run:
\`\`\`bash
./scripts/release.sh ${VERSION} --tag
\`\`\`
EOF
)")

success "Pull request created: ${PR_URL}"

echo ""
info "Next steps:"
echo "  1. Review & merge the PR: ${PR_URL}"
echo "  2. After merge, run: $0 ${VERSION} --tag"

# ── Early exit (PR flow) ───────────────────────────────────────────────────
if [[ "${2:-}" != "--tag" ]]; then
  exit 0
fi

# ── Step 5: Tag merged master (--tag mode) ──────────────────────────────────
info "Tagging release on ${MASTER_BRANCH}..."

git fetch origin "$MASTER_BRANCH"
git checkout "$MASTER_BRANCH"
git pull origin "$MASTER_BRANCH"

# Verify the version in master matches
MASTER_VERSION=$(python -c "import re; print(re.search(r\"__version__\s*=\s*['\"](.+?)['\"]\", open('${INIT_FILE}').read()).group(1))")
if [[ "$MASTER_VERSION" != "$VERSION" ]]; then
  error "Version in ${MASTER_BRANCH} is '${MASTER_VERSION}', expected '${VERSION}'. Was the PR merged?"
fi

confirm "Create and push tag '${TAG}'? This will trigger the release pipeline."

git tag -a "$TAG" -m "Release ${VERSION}"
git push origin "$TAG"
success "Tag ${TAG} pushed — release pipeline triggered"

# Back to develop
git checkout "$DEVELOP_BRANCH"
success "Back on ${DEVELOP_BRANCH}"

echo ""
success "Release ${VERSION} complete!"
echo "  PyPI + Docker publish will run via GitHub Actions."
echo "  Monitor: https://github.com/eventum-project/eventum-generator/actions"
