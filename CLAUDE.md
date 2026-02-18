# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Eventum is a flexible synthetic event generation platform. It uses a plugin-based pipeline (Input → Event → Output) to generate, transform, and deliver events. Python 3.13+, Apache 2.0 licensed, v2.0.0.

## Commands

```bash
# Dependencies (uses uv)
uv sync                          # Install all dependencies

# Running
uv run eventum run -c eventum.yml         # Run full app with config
uv run eventum generate --path gen.yml    # Run a single generator

# Testing
uv run pytest                    # Run all tests (with coverage → htmlcov/)
uv run pytest eventum/core/tests/        # Run tests for a specific package

# Code quality
uv run ruff check .              # Lint (ALL rules enabled, see pyproject.toml for ignores)
uv run ruff format .             # Format
uv run mypy eventum/             # Type check (strict, Pydantic plugin)

# Keyring management
uv run eventum-keyring           # Manage encrypted secrets

# Changelog
git cliff -o CHANGELOG.md        # Generate changelog via git-cliff
```

## Architecture

### Plugin Pipeline

The core abstraction is a three-stage pipeline: **Input → Event → Output**. Each stage is a plugin type.

- **Input plugins** generate timestamps (when events should occur): `cron`, `timer`, `linspace`, `timestamps`, `time_patterns`, `static`, `http`
- **Event plugins** produce event content from timestamps: `template` (Jinja2 + Faker/Mimesis), `script` (custom Python), `replay` (replay recorded events)
- **Output plugins** deliver events to destinations: `stdout`, `file`, `clickhouse`, `opensearch`, `http`

Plugins live in `eventum/plugins/{input,event,output}/plugins/<name>/plugin.py`.

### Plugin System

Plugins self-register via `__init_subclass__`. When a plugin class is defined, it's inspected for its module path (`eventum.plugins.<type>.plugins.<name>.plugin`) and automatically registered in `PluginsRegistry`. The loader uses lazy import + caching to load plugins on demand.

Key classes:
- `Plugin[ConfigT, ParamsT]` — abstract base in `eventum/plugins/base/plugin.py`
- `PluginsRegistry` — class-level dict registry in `eventum/plugins/registry.py`
- `loader.py` — `load_input_plugin()`, `load_event_plugin()`, `load_output_plugin()` with `@cache`

Each plugin has a `config.py` (Pydantic model) and `plugin.py` (implementation) within its directory.

### Execution Flow

1. **CLI** (`eventum/cli/commands/eventum.py`) → `run` (full app) or `generate` (single generator)
2. **App** (`eventum/app/main.py`) reads `eventum.yml` settings, loads `startup.yml` generator list, starts `GeneratorManager`
3. **Generator** (`eventum/core/generator.py`) runs in a dedicated thread: loads config → initializes plugins → creates Executor
4. **Executor** (`eventum/core/executor.py`) orchestrates the async pipeline:
   - Input plugins produce timestamps into a `janus.Queue` (sync→async bridge)
   - Event plugin consumes timestamps, produces event strings into another queue
   - Output plugins consume events with concurrent async writes
   - Uses `uvloop` for the async event loop

### Server

`eventum/server/main.py` builds a FastAPI app with pluggable services (API and UI), injected via `inject_service()` pattern. API routers are in `eventum/api/routers/` organized by resource (auth, generators, instance, preview, secrets, startup, generator_configs, docs).

### Key Packages

- `eventum/app/` — App class, GeneratorManager, Pydantic settings/models
- `eventum/core/` — Generator, Executor, config loading, plugin initialization
- `eventum/plugins/` — Plugin base classes, registry, loader, all plugin implementations
- `eventum/api/` — FastAPI routers and dependencies
- `eventum/cli/` — Click commands (`eventum`, `eventum-keyring`)
- `eventum/server/` — Server app builder, service injection
- `eventum/security/` — Keyring/cryptfile credential management
- `eventum/logging/` — Structlog configuration and context propagation

## Conventions

- **Style**: Ruff with ALL rules enabled, 79-char line length, single quotes
- **Types**: Strict mypy with Pydantic plugin; full type annotations required
- **Docstrings**: NumPy-style (Parameters/Returns/Raises sections)
- **Errors**: Custom `ContextualError` base class with `context` dict for structured error info
- **Logging**: Structlog with bound context (`generator_id`, `plugin_name`, `plugin_type`, etc.)
- **Async**: uvloop + janus queues for sync↔async bridging
- **Config**: Pydantic models for all configuration; YAML files parsed with PyYAML
- **Commits**: Conventional commits (`feat`, `fix`, `refactor`, `test`, `docs`, etc.) — git-cliff generates changelog
- **Tests**: pytest with `pytest-asyncio`, `pytest-httpx`, `pytest-cov`; tests live in `*/tests/` directories within each package
