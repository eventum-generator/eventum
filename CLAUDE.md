# CLAUDE.md

Eventum is a synthetic data generation platform built around a three-stage plugin pipeline: Input (generates timestamps) -> Event (produces events) -> Output (delivers to endpoints).

## Structure

This repository is the main part of a multi-repo workspace at `../`:

- `eventum/` (this repo) - Python backend, CLI, HTTP API, and the Studio UI
- `../docs/` - Next.js + Fumadocs documentation site deployed to https://eventum.run
- `../content-packs/` - ready-to-use generator projects that produce realistic data

Inside this repo, the Python package `eventum/` is organized as:

- `plugins/` - plugins of eventum (`input/`, `event/`, `output/`)
- `core/` - generation engine that wires plugins into pipeline
- `api/` - FastAPI routers, models, middleware for the HTTP API
- `ui/` - React/TypeScript frontend for Eventum Studio UI
- `server/` - HTTP server entry point that wires HTTP API, UI and other services
- `app/` - top-level application orchestrating generators and the server
- `cli/` - CLI commands (`run`, `generate`, `eventum-keyring` etc.)
- `logging/`, `security/`, `utils/` - supporting packages
- `www/` - bundled static UI assets shipped with the package

Alongside the package at the repo root:

- `config/` - reference `eventum.yml` and `startup.yml` configurations
- `LOGGING.md` - structured logging data model (field names, types, semantics) - `structlog` context keys should follow it

## Stack

**Backend** (`eventum/`):
- Package manager: `uv`
- Build backend: `hatchling`
- Lint + format: `ruff`
- Type check: `mypy` (standard mode)
- Tests: `pytest`
- Validation: Pydantic
- Logging: `structlog`

**Frontend** (`eventum/ui/`):
- Package manager: `pnpm`
- Build tool: Vite
- Lint: ESLint
- Format: Prettier
- Type check: `tsc`
- Components library: Mantine
- Validation: Zod

All app can run in Docker.

## Commands

Project-specific invocations that aren't obvious from the Stack section:

- Run the full application: `uv run eventum run -c <eventum.yml>`
- Run a single generator: `uv run eventum generate --path <generator.yml> --id test --live-mode true`

Standard tool invocations (`uv run pytest`, `uv run ruff check`, `uv run mypy eventum/`, `pnpm build`) follow directly from the Stack section.

## Style

- **Python style**: 79-character lines for code and 72-character lines for docstrings. ASCII only in code, comments, and docstrings.
- **Python typing and docstrings**: Full types and complete docstrings on public interfaces. Internal one-liners are fine, unless the logic is non-trivial.
- **Dashes**: Use a single hyphen `-` instead of em dash `—` in source code. The em dash `—` is allowed for MDX prose under `../docs/`.

## Hard rules

- **Commands**: Run appropriate commands through `uv run`. Don't invoke `python`, `pytest`, `ruff`, or `mypy` directly to avoid environment errors.
- **Tests** are co-located under `<package>/tests/test_<name>.py`. Every feature or bug fix ships with tests.
- **Branches**: Use git-flow model. Feature branches are created off `develop`, never off `master`.
- **Commits**: Use conventional commits. Valid scopes are top level packages names.

## Common rules

- **Never commit or push** unless the user explicitly asks.
- **Respect user edits**: Never re-add content the user has deleted. Fix the root cause of errors - do not work around them by editing configs or method contracts.
- **Surface problems honestly**: Report failed commands, flag uncertainty, raise assumptions and risks explicitly. Do not proceed silently over unknowns.
- **Depth before ascending**: Fully understand what is in front of you before moving up the stack or on to the next step. Gaps at the base compound upward into bigger mistakes.
- **Analyze before acting**: A user request is a hypothesis to weigh, not a command to execute. Before applying a change, check whether it's actually the right move - does it fit the existing design, duplicate an existing rule, create inconsistency? Surface concerns first; don't execute silently if something feels off.
- **Engaged, not compliant**: Treat each problem as worth exploring - weigh approaches, aim for the best solution you can see. When you have technical grounds to disagree, defend your position with reasoning. Do not cave to user pressure without new evidence - sycophancy hurts more than honest pushback.
- **Proactive**: Flag improvements, risks, and inconsistencies you notice even when not asked. Silence on things that are clearly off is not helpful.
- **Writing style**: No AI-tone, emoji filler, ASCII art, or marketing fluff. Verify features against real code - never invent behavior or capabilities.
- **Minimalism**: Weigh every word - each must earn its place. Brief, dense, clear facts. No filler, redundancy, or commentary.
