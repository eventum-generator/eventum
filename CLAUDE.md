# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Eventum is a flexible synthetic event generation platform built in Python 3.13+. It uses a plugin-based three-stage pipeline (**Input → Event → Output**) to generate timestamps, transform them into events, and deliver events to various destinations. Apache 2.0 licensed, current version 2.0.2.

- **Package name on PyPI**: `eventum-generator`
- **Homepage**: https://eventum.run
- **Source**: https://github.com/eventum-generator/eventum
- **Documentation site**: lives in `../docs/` (Next.js + Fumadocs, separate repo)

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
uv run pytest eventum/plugins/input/plugins/cron/tests/  # Run specific plugin tests

# Code quality
uv run ruff check .                        # Lint (ALL rules enabled, see pyproject.toml)
uv run ruff format .                       # Format (single quotes, 79-char lines)
uv run mypy eventum/                       # Type check (strict, Pydantic plugin)

# Secret management
uv run eventum-keyring                     # Manage encrypted secrets via CLI

# Changelog generation
git cliff -o CHANGELOG.md                  # Generate changelog via git-cliff

# Release (two-phase)
./scripts/release.sh <version>             # Phase 1: bump, lint, test, push, create PR
./scripts/release.sh <version> --tag       # Phase 2: tag merged master, trigger CI
```

## Architecture

### Package Structure

```
eventum/
├── __init__.py          # __version__ = '2.0.2'
├── api/                 # FastAPI REST API routers and dependencies
│   ├── dependencies/    # FastAPI Depends injection (app, settings, manager)
│   ├── routers/         # Route groups: auth, docs, generator_configs, generators,
│   │                    #   instance, preview, secrets, startup
│   └── tests/           # API integration tests
├── app/                 # Application lifecycle
│   ├── main.py          # App class (manages generators, starts server)
│   ├── manager.py       # GeneratorManager (collections of Generator instances)
│   ├── hooks.py         # InstanceHooks TypedDict (terminate, restart callbacks)
│   └── models/          # Settings, PathParameters, ServerParameters, etc.
├── cli/                 # Click CLI commands
│   └── commands/        # eventum (run/generate) and eventum-keyring
├── core/                # Generator engine
│   ├── generator.py     # Generator (thread-wrapped lifecycle manager)
│   ├── executor.py      # Executor (async pipeline: input→event→output)
│   ├── config.py        # GeneratorConfig (frozen Pydantic model)
│   ├── config_loader.py # YAML + Jinja2 templating + secret substitution
│   ├── parameters.py    # GeneratorParameters, BatchParameters, QueueParameters
│   └── plugins_initializer.py  # Plugin instantiation from config
├── plugins/             # Plugin system (see Plugin System section)
│   ├── base/            # Plugin ABC, PluginConfig base
│   ├── registry.py      # PluginsRegistry (auto-populated via __init_subclass__)
│   ├── loader.py        # Lazy plugin loading with @cache
│   ├── fields.py        # Shared plugin field types
│   ├── exceptions.py    # Plugin-specific exceptions
│   ├── input/           # Input plugins + shared utils (batcher, scheduler, merger)
│   ├── event/           # Event plugins
│   └── output/          # Output plugins + formatters
├── server/              # FastAPI app builder with service injection
│   ├── main.py          # build_server_app() with API + UI services
│   └── services/        # api/ and ui/ injectors
├── security/            # Keyring-based secret storage (keyrings-cryptfile)
├── logging/             # Structlog + Python logging config, context propagation
├── utils/               # fs_utils, json_utils, package_utils, throttler, etc.
├── ui/                  # React/TypeScript frontend (Vite + React)
└── www/                 # Built UI bundle (served by FastAPI in app mode)
```

### Plugin Pipeline

The core abstraction is a three-stage pipeline. Each generator config wires together plugins from each stage:

```yaml
# GeneratorConfig structure (generator.yml)
input:          # list[PluginConfig], min 1 — when to generate
  - cron: { ... }
event:          # single PluginConfig — what to generate
  template: { ... }
output:         # list[PluginConfig], min 1 — where to send
  - stdout: { ... }
```

**Input plugins** — generate timestamps (`NDArray[datetime64]`):
| Plugin | Description |
|--------|-------------|
| `cron` | Cron expression with optional start/end range, count per interval |
| `timer` | Fixed-interval timer (seconds between timestamps, repeat cycles) |
| `linspace` | Evenly spaced timestamps between start and end |
| `timestamps` | Explicit list of timestamps or path to file |
| `time_patterns` | Complex patterns with oscillator, multiplier, randomizer, spreader |
| `static` | Fixed count of timestamps at current time |
| `http` | HTTP server that accepts timestamps via requests (interactive) |

**Event plugins** — produce event strings from timestamps:
| Plugin | Description |
|--------|-------------|
| `template` | Jinja2 templates with Faker/Mimesis, 6 picking modes (all/any/chance/spin/fsm/chain), samples, shared/local/global state |
| `script` | Custom Python script with `produce(params: dict) -> list[str]` |
| `replay` | Replay events from a log file with optional timestamp substitution |

**Output plugins** — deliver events to destinations:
| Plugin | Description |
|--------|-------------|
| `stdout` | Print to stdout/stderr with configurable flush interval |
| `file` | Write to file (append/overwrite, rotation support) |
| `clickhouse` | ClickHouse via HTTP (configurable format, SSL, proxy) |
| `opensearch` | OpenSearch cluster (SSL, proxy, bulk indexing) |
| `http` | Generic HTTP endpoint (any method, auth, SSL) |

**Output formatters** (configured per output plugin via `formatter` field):
| Format | Description |
|--------|-------------|
| `plain` | Plain text (default for stdout/file) |
| `json` | Single JSON object per event |
| `json-batch` | JSON array of events |
| `template` | Custom Jinja2 template per event |
| `template-batch` | Custom Jinja2 template for batch of events |
| `eventum-http-input` | Format compatible with eventum HTTP input plugin |

### Plugin System

Plugins self-register via `__init_subclass__`. When a class like `class CronPlugin(InputPlugin[CronConfig, InputPluginParams])` is defined, the metaclass inspects its module path (`eventum.plugins.<type>.plugins.<name>.plugin`) and registers it in `PluginsRegistry`. The loader uses lazy import + `@cache` to load plugins on demand.

Plugin directory convention:
```
eventum/plugins/{input,event,output}/plugins/<name>/
├── config.py    # Pydantic config model (frozen)
├── plugin.py    # Plugin implementation
└── tests/       # Plugin-specific tests
```

Key base classes and contracts:
- `Plugin[ConfigT, ParamsT]` — ABC in `eventum/plugins/base/plugin.py`. Provides `name`, `type`, `id`, `guid`, `logger`, `config`, `base_path`, `resolve_path()`
- `InputPlugin` — `generate(size, *, skip_past) -> Iterator[NDArray[datetime64]]`
- `EventPlugin` — `produce(params: ProduceParams) -> list[str]` where `ProduceParams = {timestamp: datetime, tags: tuple[str, ...]}`
- `OutputPlugin` — async `open()`, `write(events: Sequence[str])`, `close()`; has concurrency semaphore

### Execution Flow

1. **CLI** (`eventum/cli/commands/eventum.py`) → `run` (full app) or `generate` (single generator)
2. **App** (`eventum/app/main.py`) loads `eventum.yml` settings + `startup.yml` generator list, starts `GeneratorManager`, launches FastAPI server on port 9474
3. **Generator** (`eventum/core/generator.py`) runs in a dedicated thread: loads YAML config → initializes plugins → creates Executor
4. **Executor** (`eventum/core/executor.py`) orchestrates the async pipeline with `uvloop`:
   - Input plugins produce timestamps → `janus.Queue` (sync→async bridge)
   - Timestamps are batched (by `batch.size` / `batch.delay`)
   - Scheduler applies live_mode timing (waits until timestamp moment)
   - Event plugin consumes timestamps, produces event strings → events queue
   - Output plugins consume events with concurrent async writes (semaphore-controlled)
   - Throttler applies rate limits

### Configuration System

**App config** (`eventum.yml`) — flat dot-notation YAML:
```yaml
server.host: "0.0.0.0"
server.port: 9474
server.auth.user: eventum
server.auth.password: eventum
generation.timezone: UTC
generation.batch.size: 10000
generation.batch.delay: 1.0
generation.queue.max_timestamp_batches: 10
generation.queue.max_event_batches: 10
generation.keep_order: false
generation.max_concurrency: 100
generation.write_timeout: 10
log.level: info
log.format: plain                # plain | json
log.max_bytes: 10485760          # 10 MiB
log.backups: 5
path.logs: /app/logs/            # must be absolute
path.startup: /app/config/startup.yml
path.generators_dir: /app/config/generators/
path.keyring_cryptfile: /app/config/cryptfile.cfg
path.generator_config_filename: generator.yml
```

**Generator config** — YAML with Jinja2 templating:
- `${ params.name }` — substituted from CLI `--params` or startup.yml `params` dict
- `${ secrets.name }` — resolved from encrypted keyring at runtime
- Validated as `GeneratorConfig` (frozen Pydantic model) after substitution

**Startup config** (`startup.yml`) — list of generators to auto-start:
```yaml
- id: "my-generator"
  path: "/absolute/path/to/generator.yml"
  autostart: true              # default: true
  live_mode: true              # default: true
  skip_past: true              # default: true
  params: { key: value }       # optional, for Jinja2 substitution
  # Generation parameters can be overridden per-generator:
  # batch.size, batch.delay, timezone, keep_order, etc.
```

### REST API

FastAPI server at port 9474. All API routes under `/api/` prefix. Basic auth with HttpOnly cookie session.

**Generators** (`/api/generators/`):
- `GET /` — list all generators with status
- `GET /{id}`, `POST /{id}`, `PUT /{id}`, `DELETE /{id}` — CRUD
- `POST /{id}/start`, `POST /{id}/stop` — lifecycle
- `GET /{id}/status`, `GET /{id}/stats` — monitoring
- `WebSocket /{id}/logs` — real-time log streaming
- `GET /group-actions/stats-running` — stats for all running
- `POST /group-actions/bulk-start`, `bulk-stop`, `bulk-delete` — batch operations

**Startup** (`/api/startup/`):
- `GET /`, `GET /{id}`, `POST /{id}`, `PUT /{id}`, `DELETE /{id}` — manage startup list
- `POST /group-actions/bulk-delete`

**Instance** (`/api/instance/`):
- `GET /info` — app and host information
- `GET /settings`, `PUT /settings` — settings management
- `POST /stop`, `POST /restart` — instance lifecycle
- `WebSocket /logs/main` — main log streaming

**Preview** (`/api/preview/{name}/`):
- `POST /input-plugins/generate` — preview timestamp generation
- `POST /event-plugin`, `POST /event-plugin/produce`, `DELETE /event-plugin` — preview events
- Template state endpoints (local/shared/global) for GET/PATCH/DELETE
- `POST /formatter/format` — preview formatter output
- `POST /versatile-datetime/normalize` — parse date expressions

**Secrets** (`/api/secrets/`): `GET /`, `GET /{name}`, `PUT /{name}`, `DELETE /{name}`

**Auth** (`/api/auth/`): `POST /login`, `GET /me`, `POST /logout`

**Docs** (`/api/docs/`): `GET /asyncapi.yml`, `GET /asyncapi`

### Dependency Injection (FastAPI)

App state is stored on `FastAPI.state` and exposed via `Depends()`:
```python
# eventum/api/dependencies/app.py
AppDep = Annotated[FastAPI, Depends(get_app)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
GeneratorManagerDep = Annotated[GeneratorManager, Depends(get_generator_manager)]
InstanceHooksDep = Annotated[InstanceHooks, Depends(get_instance_hooks)]
```

### Web UI

React/TypeScript SPA in `eventum/ui/` (Vite build). Built bundle served from `eventum/www/` by the FastAPI UI service. The UI is excluded from the wheel build source but the `www/` built assets are included as artifacts.

## Key Models

| Model | Location | Purpose |
|-------|----------|---------|
| `Settings` | `eventum/app/models/settings.py` | Top-level app configuration |
| `PathParameters` | `eventum/app/models/parameters/path.py` | All paths (must be absolute) |
| `ServerParameters` | `eventum/app/models/parameters/server.py` | Host, port, SSL, auth |
| `GenerationParameters` | `eventum/app/models/parameters/generation.py` | Timezone, batch, queue, concurrency |
| `LogParameters` | `eventum/app/models/parameters/log.py` | Level, format, rotation |
| `GeneratorConfig` | `eventum/core/config.py` | Per-generator plugin wiring (frozen) |
| `GeneratorParameters` | `eventum/core/parameters.py` | Per-generator runtime params |
| `BatchParameters` | `eventum/core/parameters.py` | Batch size/delay (at least one required) |
| `QueueParameters` | `eventum/core/parameters.py` | Max batches in timestamp/event queues |
| `ProduceParams` | `eventum/plugins/event/base/plugin.py` | `{timestamp, tags}` passed to event plugins |
| `PluginConfig` | `eventum/plugins/base/config.py` | Base for all plugin configs (frozen) |
| `PluginInfo` | `eventum/plugins/registry.py` | Registry entry: name, cls, config_cls, type |
| `InstanceHooks` | `eventum/app/hooks.py` | TypedDict callbacks for terminate/restart |
| `GeneratorManager` | `eventum/app/manager.py` | Dict-like container for Generator instances |

## Testing

Tests are co-located with their packages in `*/tests/` directories. ~90 test files covering all packages and plugins.

```bash
uv run pytest                                    # All tests with coverage
uv run pytest eventum/api/tests/                 # API tests
uv run pytest eventum/core/tests/                # Core engine tests
uv run pytest eventum/plugins/tests/             # Plugin system tests
uv run pytest eventum/plugins/input/plugins/cron/tests/  # Specific plugin
```

**Test configuration** (`pyproject.toml`):
- `pytest-cov` for coverage (HTML report in `htmlcov/`)
- `pytest-asyncio` for async tests
- `pytest-httpx` for HTTP mocking
- Coverage omits: `*/models/*`, `*/logging/config.py`, `*/cli/splash_screen.py`, `*/tests/*`

## Build and Deployment

**Build system**: hatchling (PEP 517). Version sourced from `eventum/__init__.py`.

**Docker** (multi-stage):
1. `app-build` — Python 3.13-slim + uv, sync dependencies
2. `ui-build` — Node 24-slim, build React UI
3. `final` — Python 3.13-slim, copy `.venv` + built UI into `eventum/www/`
4. Entrypoint: `eventum run -c /app/config/eventum.yml`, port 9474

**Wheel**: includes `eventum/` package + `eventum/www/` built assets, excludes `eventum/ui/` source and `**/tests/`

## Conventions

- **Package manager**: uv
- **Style**: Ruff with ALL rules enabled (`select = ["ALL"]`), 79-char line length, single quotes
- **Ignored rules**: `A001`, `A002`, `A006` (builtin shadowing), `ANN401` (Any type), `D105` (magic method docs), `D205` (blank line after summary), `FIX002` (TODO), `S311` (non-crypto random), `S701` (Jinja2 autoescape), `TRY400` (error-instead-of-exception)
- **Per-file ignores**: `eventum/api/routers/**/routes.py` — `D103` (undocumented functions), `FAST003` (unused path param)
- **Linting excludes**: `**/tests/**`
- **Types**: Strict mypy with Pydantic plugin; full type annotations required
- **Docstrings**: NumPy-style (Parameters/Returns/Raises sections)
- **Errors**: Custom `ContextualError` base class with `context: dict` for structured error metadata
- **Logging**: Structlog with bound context variables (`generator_id`, `plugin_name`, `plugin_type`, etc.)
- **Async**: uvloop + janus queues for sync↔async bridging
- **Config models**: All Pydantic, frozen where immutability is needed
- **Commits**: Conventional commits (`feat`, `fix`, `refactor`, `test`, `docs`, etc.) — git-cliff generates changelog
- **Git**: Main branch is `master`, development on `develop`

## Common Gotchas

- **GeneratorConfig keys must be real plugin names** — the config `input: [{cron: {...}}]` uses the actual plugin name `cron`, not arbitrary identifiers
- **PathParameters requires absolute paths** — all paths in `eventum.yml` path section must be absolute
- **Script plugin `produce()` takes a dict** — `produce(params: dict)`, not separate keyword arguments
- **Interactive input plugins block others** — HTTP input plugin is interactive and cannot be merged with other inputs in the same generator
- **Config Jinja2 tokens** — use `${ params.key }` and `${ secrets.name }` syntax (with spaces inside braces)
- **FastAPI state injection** — app state (`generator_manager`, `settings`, `instance_hooks`) must be set before first request; patches must be active during request handling, not just at registration time
- **Batch parameters** — at least one of `batch.size` or `batch.delay` must be set
- **Timezone** — uses pytz timezone objects internally, config accepts string identifiers
