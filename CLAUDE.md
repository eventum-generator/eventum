# CLAUDE.md

Eventum is a synthetic event generation platform with a three-stage plugin pipeline (Input → Event → Output). Python 3.13+, Apache 2.0 licensed.

- **Package name**: `eventum-generator`
- **Homepage**: https://eventum.run
- **Source**: https://github.com/eventum-generator/eventum
- **Sibling repos**: `../docs/` (Next.js documentation site), `../content-packs/` (ready-to-use generators)

## Commands

```bash
# Dependencies (uses uv as package manager)
uv sync                                    # Install all dependencies

# Running
uv run eventum run -c eventum.yml          # Run full app (server + generators)
uv run eventum generate --path gen.yml     # Run a single generator (no server)

# Testing
uv run pytest                              # Run all tests (with coverage → htmlcov/)
uv run pytest eventum/core/tests/          # Run tests for a specific package

# Code quality
uv run ruff check .                        # Lint (ALL rules enabled, see pyproject.toml)
uv run ruff format .                       # Format (single quotes, 79-char lines)
uv run mypy eventum/                       # Type check (strict, Pydantic plugin)

# Changelog generation
git cliff -o CHANGELOG.md                  # Generate changelog via git-cliff

# Release (two-phase)
./scripts/release.sh <version>             # Phase 1: bump, lint, test, push, create PR
./scripts/release.sh <version> --tag       # Phase 2: tag merged master, trigger CI
```

## Conventions

- **Package manager**: uv
- **Style**: Ruff with ALL rules enabled (`select = ["ALL"]`), 79-char line length, single quotes
- **Ignored rules**: `A001`, `A002`, `A006`, `ANN401`, `D105`, `D205`, `FIX002`, `S311`, `S701`, `TRY400`
- **Per-file ignores**: `eventum/api/routers/**/routes.py` — `D103`, `FAST003`
- **Linting excludes**: `**/tests/**`
- **Types**: Strict mypy with Pydantic plugin; full type annotations required
- **Docstrings**: NumPy-style (Parameters/Returns/Raises sections). Public API only.
- **ASCII only in code**: Never use characters that can't be typed on a standard keyboard in code, comments, commit messages, or CLI output. Use `->` not `→`, `-` not `—`, `<-` not `←`, `!=` not `≠`, `*` not `•`, etc. Unicode symbols are fine in prose/docs MDX content only.
- **Errors**: Custom `ContextualError` base class with `context: dict` for structured error metadata
- **Logging**: Structlog with bound context variables (`generator_id`, `plugin_name`, `plugin_type`, etc.)
- **Config models**: All Pydantic, frozen where immutability is needed
- **Commits**: Conventional commits (`feat`, `fix`, `refactor`, `test`, `docs`, etc.) — git-cliff generates changelog. Scopes: app, api, cli, core, logging, plugins, security, ui, utils, server.
- **Git**: Main branch is `master`, development on `develop`
- **Performance**: Optimize for high throughput. Cache computed values, pre-build objects at init time, minimize per-call allocations, use O(1) lookups over linear scans.
- **Tests**: Co-located in `*/tests/` directories. Every feature/fix must have tests.
- Don't commit unless explicitly asked

## Cross-cutting Change Checklist

A feature is not complete until every affected layer is updated.

| What changed | Must update |
|---|---|
| **New plugin** | Plugin dir + Pydantic config + Zod schema + UI union index + UI form component + MDX doc page + `meta.json` nav |
| **Rename plugin** | All of above + content-packs `generator.yml` files + changelog |
| **Plugin config field** | Pydantic model + Zod schema + UI form component + MDX docs |
| **Template context variable** | Template plugin + `globals.ts` autocomplete + `template.mdx` docs + content-packs `api-reference.md` |
| **Template module function** | `modules/<name>.py` + tests + `globals.ts` autocomplete + `template.mdx` docs + content-packs `api-reference.md` |
| **API route** | FastAPI router + re-export OpenAPI spec + `pnpm generate-api-docs` + UI API calls if applicable |
| **New formatter** | Output base plugin + Zod schemas + `FormatterParams.tsx` + `formatters.mdx` |
| **New release** | `eventum/__init__.py` version + CHANGELOG.md (git-cliff) + docs changelog MDX page + `meta.json` |

## Workflow Orchestration

- **Always test** — every feature/fix must have tests. No exceptions.
- **Full verification** — run tests + lint + type check before presenting results.
- **Same-session docs** — if a change affects user-facing behavior, update docs in `../docs/content/docs/` in the same session.
- **Fix trivial issues** — fix obvious issues (typos, dead imports, clear bugs) near the code you're changing. Ask before bigger refactors.

### 1. Plan Mode Default

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don’t keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy

- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop

- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: “Would a staff engineer approve this?”
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask “is there a more elegant way?”
- If a fix feels hacky: “Knowing everything I know now, implement the elegant solution”
- Skip this for simple, obvious fixes — don’t over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don’t ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what’s necessary. Avoid introducing bugs.
