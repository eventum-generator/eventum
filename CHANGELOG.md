# Changelog

All notable changes to this project will be documented in this file.

## 2.2.0 (2026-02-27)

### 🚀 New Features

- Add systemd service management to CLI — install, uninstall, start, stop, restart, and check status of Eventum as a systemd service
- Implement weighted sampling for CSV and JSON — select sample rows by weight column for non-uniform data generation
- Add per-template variables in TemplateEventPlugin — templates can define their own local variables alongside shared ones
- Add random distribution functions — new `rand.gauss`, `rand.triangular`, `rand.expo`, `rand.lognorm`, `rand.beta`, and `rand.pareto` methods
- Support dict input for `rand.weighted_choice` — pass weight mappings directly without a separate sample file

### 🐛 Bug Fixes

- Add `quotechar` config to CSV sample reader and improve error message for inconsistent column counts
- Ensure intermediate directories are created for file output plugin
- Update community links to GitHub Discussions in Eventum Studio navbar and footer

### 🧪 Testing

- Add comprehensive tests for systemd service CLI commands and service manager
- Add tests for weighted sampling (CSV and JSON, with and without weights)
- Add tests for new random distribution functions
- Add tests for file output plugin directory creation

### 📝 Other Changes

- Remove PROPOSALS.md — proposals are now created as GitHub issues
- Add Claude Code skills for plugin creation, release management, and issue implementation

## 2.1.0 (2026-02-21)

### 🚀 New Features

- Add named access for CSV and JSON samples — access sample data by column name in templates (e.g., `sample.column_name` instead of `sample[0]`)
- Add placeholder support in Eventum Studio — plugin config forms now accept `${params.*}` and `${secrets.*}` placeholders
- Introduce relaxed generator configuration model — API returns configs with placeholders without validation errors

### 🐛 Bug Fixes

- Fix missing dataset headers — generate default column headers when CSV/JSON samples lack them
- Fix YAML comments breaking config loading — strip full-line comments before Jinja2 template processing
- Fix file output plugin not closing file before reopening in `_write` method
- Fix heterogeneous JSON samples with inconsistent keys across records
- Fix stdout output plugin using `writelines()` — switch to `write()` to avoid bugs on specific platforms
- Fix template plugin params schema to allow any type of values in common fields (Eventum Studio)
- Fix `RootModel` subclass handling in type relaxation of API models
- Fix image URLs in README.md to use absolute paths

### ⚡ Performance

- Migrate from `pytz` to `zoneinfo` — up to 2x speedup in event producing

### 🧪 Testing

- Add tests for generator configs with placeholder support
- Add tests for heterogeneous JSON sample handling
- Add tests for config loader YAML comment stripping
- Add tests for named and index-based sample access
- Update CSV sample tests for numeric access and improve assertions
- Suppress deprecation warnings for date parsing in tests
- Update session handling in auth tests for consistency

### 📝 Other Changes

- Add Eventum Improvement Proposals document
- Format JSON output for default values in `TemplateEventPluginParams`, `HTTPOutputPluginParams`, and `OpensearchOutputPluginParams`

## 2.0.2 (2026-02-21)

### 🐛 Bug Fixes

- Fix generator config API GET endpoint returning validation error when config contains `${params.*}` or `${secrets.*}` placeholders — use loose validation for reading and strict validation for creating/updating

### 🧪 Testing

- Add test for reading generator configs with placeholders via API

### 📝 Other Changes

- Update GitHub URLs in README and pyproject.toml to match new organization
- Improve release script with detailed usage instructions and phase handling

## 2.0.1 (2026-02-21)

### 🐛 Bug Fixes

- Fix `--params` CLI option not accepting JSON input — added proper JSON parsing for dict-type Click parameters
- Fix pydantic validation error when validating file path extensions (`.csv`, `.json`, `.jinja`) — replaced `Field(pattern=...)` with `@field_validator` on `Path` fields

### 🧪 Testing

- Add comprehensive tests for API endpoints (auth, generators, configs, instances, startup, secrets, file tree, timestamps aggregation)
- Add tests for app models (generators, parameters)
- Add tests for CLI keyring commands and pydantic converter
- Add tests for core config loader, generator, initializer, and parameters
- Add tests for ClickHouse and stdout output plugin configs
- Add tests for server main and UI routes

### 📝 Other Changes

- Update app slogan in CLI splash screen
- Update documentation links
- Add Codecov badge to CI
- Add HTML report export to CI
- Fix Docker build

## 2.0.0 (2026-02-20)

### 🚀 Features

#### Input plugins

- New `http` input plugin — trigger event generation from external systems via HTTP requests
- Live & sample modes for all input plugins — run in real-time or generate as fast as possible
- Human-readable dates — write `"January 1, 2025"`, `"+1h"`, or `"now"` instead of strict ISO formats
- Multiple input merging — combine several input plugins in one generator with automatic timestamp ordering

#### Event plugins

- New `script` plugin — write event logic as a Python function when templates aren't enough
- New `replay` plugin — replay events from existing log files with optional timestamp replacement

#### Template plugin enhancements

- Faker & Mimesis — two powerful data generation libraries available directly in templates (70+ locales, hundreds of data providers)
- `module` gateway — access any installed Python package in templates via `module.<package>`
- Global state — new `globals` scope for sharing state across all generators (thread-safe)
- New state methods — `update`, `clear`, and `as_dict` for all state scopes
- New picking modes — `fsm` (finite state machine) and `chain` (fixed sequence)
- New sample types — `json` and `items` (inline lists in YAML)
- Timezone-aware timestamps — `timestamp` is now a proper `datetime` object, not a string
- Better subprocesses — new `cwd`, `env`, and `timeout` options

#### Output plugins

- New `clickhouse` plugin — write events directly to ClickHouse
- New `http` plugin — send events to any HTTP endpoint
- Formatters — transform events before delivery with `plain`, `json`, `json-batch`, `template`, or `template-batch`

#### Existing output plugin improvements

- **File** — new `flush_interval`, `cleanup_interval`, `file_mode`, `write_mode`, `encoding`, and `separator` options
- **Stdout** — new `flush_interval`, `stream`, `encoding`, and `separator` options
- **OpenSearch** — new `connect_timeout`, `request_timeout`, `client_cert`, `client_cert_key`, and `proxy_url` options

### ⚡ Performance

- Batch processing across the entire pipeline — events are grouped into configurable batches between stages, dramatically reducing overhead and improving throughput compared to 1.x

### 🧪 Testing

- Expanded test coverage for all plugins, the core executor, configuration loading, and the CLI

### 🏗️ Architecture

- Complete rewrite from scratch
- Plugin system — self-registering plugins with a consistent structure
- Async pipeline — `uvloop` event loop with `janus` queues for efficient stage-to-stage communication
- Configuration — Pydantic-based validation with `${params.*}` and `${secrets.*}` variable substitution
- CLI — rebuilt with Click, options auto-generated from config models
- REST API — new FastAPI-based API for programmatic control
- Eventum Studio — brand-new React web UI for visual editing, debugging, and monitoring

### 📝 Other changes

- `sample` input plugin renamed to `static`
- `jinja` event plugin renamed to `template`
- Structured logging via structlog — supports plain-text and JSON output
- Better error diagnostics — exceptions now carry structured context for easier troubleshooting

<!-- generated by git-cliff -->
