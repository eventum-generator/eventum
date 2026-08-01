# Changelog

All notable changes to this project will be documented in this file.

## 2.7.0 (2026-08-01)

### 🚀 New Features

#### Eventum Studio

- **Restyled every screen on one design system** — matched dark and light themes, one status palette, and consistent surfaces, controls, tables and menus
- **Rebuilt the project page into a development studio** — a docked workspace of file explorer, tabbed code editor, stage inspector and a console holding the timestamp preview, event debugger, template state and formatter. One Save covers the configuration and every edited file, and the debug tools keep their results while you move between stages. A `generator.yml` that fails to parse now opens in recovery mode with the error over the editor instead of locking the project out
- **Rebuilt the instance page into a live overview** — Overview, Settings and Logs tabs. Overview draws live throughput over the pipeline with per-plugin counters, the instance's project, mode, autostart, timezone and last run, and its scenarios with inline add and remove. The header carries live status, uptime and Start / Stop / Restart; the log viewer is embedded and streams only while its tab is open
- **Rebuilt Monitoring into a live dashboard** — animated Input → Event → Output flow with per-stage metrics, throughput and failure charts over a rolling window, each instance's share of the output load, and CPU, memory, disk and network tiles
- **Rebuilt Management into an instance console** — application and host identity (version, Python, platform, address, uptime), a CPU and memory snapshot, the application log streamed in the page instead of behind a modal, and a danger zone for restart and stop
- **Added runtime stats and filters to the tables** — running instances show Flow (average output EPS), Errors and Written as sortable columns. Projects filters by All / In use / Unused, Instances by All / Active / Inactive, Scenarios by All / Running / Inactive, each list counts its records, and every table has a first-run and a no-match state. Filters live in the URL, so a filtered view is linkable. Project rows carry instance chips that link to their instance and light up while it runs
- **Reworked Settings, Secrets and the scenario page** — Settings splits into a Server / Generation / Paths / Logging rail with Save pinned in the header and a dot on sections holding unsaved edits; Secrets adds entries through an inline form with a password field and copyable names; the scenario page gains an aggregate status header with Start all and Stop all, and inline syntax-highlighted template previews
- **Added an unsaved-changes guard** — leaving an instance or a project with unsaved changes asks for confirmation on any navigation and warns before a refresh or a closed tab; previously only the back button was covered
- **Added a Rename action to projects, instances, scenarios and secrets** — an object no longer has to be recreated to carry a different name. A renamed project moves its directory and every instance using it follows, so those instances must be stopped first; a renamed instance keeps its parameters and scenario membership; a renamed scenario has its tag rewritten on all its instances; a renamed secret keeps its value, and the dialog lists the projects reading it as `${secrets.<name>}`, since those placeholders are not rewritten
- **Added a Clone action to the instance row menu** — creates a new instance from an existing one, reusing its project and all parameters
- **Made Studio navigation link-based** — record names, sidebar items, breadcrumbs, home cards and in-page links are real links, so middle-click and Ctrl/Cmd-click open them in a new browser tab; middle-click also closes an editor tab. Selecting a record name no longer opens it, so names stay copyable
- **Added file sizes to the project file tree** — every file shows its size next to its name, and a file over 10 MB is not opened in the editor: the tab reports the size and the limit instead of transferring a file the editor cannot display. Generator output files are the usual case
- **Rebuilt the editor search panel** — Ctrl/Cmd-F opens a compact panel floating over the top-right corner of the editor instead of a strip stretched across its bottom edge. The query field counts the matches and marks a malformed expression, case, regular-expression and whole-word matching are icon toggles, and the replace row is revealed on demand
- **Lit the indicator of a live instance** — a running, starting or stopping instance carries a halo around its status indicator everywhere it appears: Home, Monitoring, Instances, Scenarios and the scenario diagram. The states at rest carry none, so a live instance reads without comparing it to anything

#### MCP

- **Added rename tools for projects, generators, scenarios and secrets** — over HTTP an agent can rename each of them with the same guards the UI applies: a renamed project moves its directory and repoints the generators using it (all of which must be stopped), a renamed generator keeps its parameters and scenario membership, a renamed scenario has its tag rewritten everywhere, and a renamed secret keeps its value without ever exposing it. `list_secret_references` reports the projects reading a secret, so the agent can name what a rename breaks; `${secrets.*}` tokens are never rewritten. Adding and reading a secret value stay outside MCP
- **Added tools for scenarios, global state, settings and instance control** — over HTTP an agent can manage scenarios (list, inspect, add or remove a generator, delete), read and edit the shared global state, read host/runtime info and the running settings (credentials redacted, absolute paths shortened), patch the settings file, and stop or restart the instance. Write tools stay gated behind `server.mcp.allow_write`; credentials cannot be changed over MCP, settings apply on the next restart, and stopping or restarting ends the agent's own connection

#### API/CLI

- **Added rename endpoints for projects, instances, scenarios and secrets** — `POST /<resource>/{key}/rename` on each of the four resources, carrying the same guards: renaming a project reports the instances it repointed and is refused while any of them is active, renaming an instance is refused while it runs, and a name already taken is refused as a conflict. `GET /secrets/{name}/references` lists the projects reading a secret as `${secrets.<name>}`
- **Reported file sizes in the generator file tree** — every file node carries its size, so a client can decide what to do with a file before requesting it; a file whose size cannot be read is reported as unknown instead of failing the whole tree

### 🐛 Bug Fixes

#### Eventum Studio

- **Gave file transfers their own request deadline** — every request from Studio shared a single 10-second deadline, so opening or uploading a large project file failed while the transfer was still running. Requests that carry file content now run without a deadline and the rest have 60 seconds; a request that does run out of time says so instead of reporting a generic failure
- **Told a finished instance apart from a running one at a glance** — Finished carried a green-teal chip that read as Active's green once diluted into a status chip, so a stopped instance looked like it was still running. A status chip now stays coloured only while an instance is live: an instance at rest takes a neutral chip and names its outcome through the status indicator alone - a deep green for finished, a deep red for failed - dark enough to read as switched off
- **Added MCP controls to the Server settings section** — the HTTP server toggle, write-tool permission, mount path and allowed hosts are now editable in Studio; previously they lived only in `eventum.yml`, and saving settings from Studio reset them to defaults
- **Cleared the cached project configuration on delete and create** — a project created with the name of a deleted one starts from a clean configuration instead of showing the old project's settings
- **Restricted the Write timeout field to whole seconds** — it accepted fractional values that the configuration then rejected on save
- **Read the cron seconds field in the generator's order** — the text under the cron Expression field took the seconds as the first field, so `35 10 * * * 3` was described as "At 35 seconds past the minute … only on Wednesday" while the generator fires at 10:35:03 every day. The description and the validity check now follow `minute hour day month weekday second year`, and the field hint spells the order out
- **Accepted cron expressions carrying random values or parameters** — `0 0 R * *` and `${params.schedule}` were rejected as invalid although the generator runs them; the field checked what could be spelled out in words rather than what the generator accepts. Both are accepted now, with a note under the field saying the schedule is resolved at run time
- **Validated the HTTP output form against its own rules** — the form checked its values against the file output's rules instead, so a malformed URL or an out-of-range response code drew no inline error and surfaced only once the configuration was read
- **Matched the plugin switches to the generator's defaults** — a field the configuration does not mention was drawn as off, so Verify SSL on the `http`, `opensearch`, `clickhouse` and `tcp` outputs read as unchecked while the generator was verifying the certificate, and Include end point on the `linspace` input read as off while the range included it. A switch now shows what the field resolves to, and an untouched field is still left out of the configuration
- **Reported the restart and the stop on the Management page** — the page went on claiming the instance was running and then reported a failure to reach it. Its status now switches to Restarting or Stopping, and the page loads afresh a moment later, so it shows the instance as it stands - running again, or unreachable
- **Cut long file names in the project file tree** — a name wider than the panel wrapped onto a second line and broke the row rhythm; it is trimmed with an ellipsis now and shown in full on hover. The file size beside it is rounded to whole units and set smaller, as metadata rather than as part of the name

#### Core

- **Stopped splitting generator configuration keys on dots** — every key holding a dot was expanded into nested keys, so a state machine comparing a state field (`ge: {shared.step: 5}`) was rejected as invalid, and a template parameter, sample or template name written with a dot arrived reshaped. A generator configuration is now read exactly as written; the dot-separated shorthand for nested settings stays in `eventum.yml`, `startup.yml` and time-pattern files, and a generator configuration spells `formatter.format: plain` out as a nested block
- **Read the dotted name of a `${params.*}` or `${secrets.*}` token as a path** — `${params.opensearch.host}` matched only a parameter whose full name was `opensearch.host`, and even then substituted nothing, so a nested parameter (the form `startup.yml` documents) and a parameter or keyring secret named with a dot were both unreachable. A token name now addresses the value spelled exactly like it or the path of nested names; a name addressing nothing is reported as missing
- **Closed streaming connections on graceful shutdown** — Ctrl+C with a live log view or a connected MCP client now exits in well under a second, instead of waiting out the shutdown timeout and printing cancellation errors
- **Scoped the network and disk figures to the Eventum process** — the Disk I/O and Network tiles measured the whole host. Disk now comes from the process and network bytes are counted inside the application; CPU and memory stay host-level, and all counters are cumulative since startup

#### Plugins

- **Restored parallel generation alongside the `clickhouse` output** — loading the plugin on free-threaded Python re-enabled the GIL for the whole process, so every generator lost parallelism, not only the one writing to ClickHouse. The ClickHouse client is now required at a version whose compiled modules keep the GIL disabled
- **Serialized the loading of plugins across generators** — starting several generators at once could leave one of them Failed during plugin initialization with an internal error naming nothing the user controls, while its siblings using the same plugin started normally, and a manual restart of that generator recovered it. On free-threaded Python two generators loading their plugins at the same moment interfered inside the construction of the configuration classes; a plugin is now loaded by one generator at a time
- **Dropped the unsatisfiable constraint on the certificate fields of the `clickhouse`, `opensearch` and `http` outputs** — `ca_cert`, `client_cert` and `client_cert_key` carried a text-length constraint that cannot apply to a path, so any value failed with a type error while the configuration was read, leaving certificate-based TLS unusable (Thanks to [Sai Asish Y](https://github.com/SAY-5) for the PR!)
- **Turned certificate verification on by default in the `opensearch` and `http` outputs** — `verify` defaulted to `false`, so an `https://` endpoint was trusted without any check unless verification was requested explicitly, while `clickhouse` and `tcp` checked the same connection. A generator writing to an endpoint with a self-signed or internal-CA certificate now fails with a certificate error: point `ca_cert` at the issuing CA, or set `verify: false` to keep the connection unchecked
- **Reported a failed bind of the `http` input as a generation error** — a generator whose port was already taken produced no timestamps and no diagnosis; it now fails with the bind address and the server exit code
- **Counted every event an output failed to deliver** — an output that loses events one by one - a request the collector rejects, a document the bulk response refuses, a message the broker drops, an event that cannot be encoded - logged each loss and subtracted it from its written count, but recorded it nowhere else, so an instance delivering nothing read exactly like an idle one: fewer written events than produced, every failure counter at zero. Those events now land in `write_failed`
- **Counted every event rejected by a formatter in the failure metrics** — `format_failed` moved only when formatting failed for a whole batch, so a single malformed event among valid ones was dropped without a trace in the instance metrics, the Monitoring dashboard and the Errors column, leaving Written short of Produced with nothing to explain the gap. The `json` and `template` formatters now count their rejections per event, and a batch rejected as a whole by `json-batch` or `template-batch` counts all of its events
- **Stopped writing an empty JSON array when `json-batch` rejects every event of a batch** — the destination received `[]` instead of nothing

#### MCP

- **Bounded what file access hands to the agent** — `read_generator_file` returned the whole file, so an output file or a large sample went into the agent's context in one piece. A call now returns at most 64 KB, 256 KB when asked for, ending on a complete line, and reports the file size with the offset to continue from, so an agent pages through anything larger. `describe_sample` parses a sample whole, the way a run loads it, so it now refuses a file above 32 MB and points at the windowed read instead. The authoring prompt tells the agent how to page a read
- **Widened the guidance given to agents** — large CSV/JSON samples go through the REST file API (over HTTP) or straight to disk (locally) instead of the slow `write_generator_file` tool. The agent is also told that templates can import any installed Python package and run shell commands via `subprocess`, that the server exposes an OpenAPI schema to fall back on when no tool fits, and how live/sample modes and scenarios work

#### API/CLI

- **Served a generator file as a snapshot of the moment it was requested** — reading an output file of a running generator aborted mid-response, because the response declared the file size before reading the file and the file kept growing. A file that cannot be read now answers with an error instead of a dropped connection
- **Moved the scenario global-state scan to a worker thread** — a scenario with many generators opens instead of hanging and failing after about ten seconds
- **Served the websocket API schema from memory** — the schema was written into the installed package on every application start, so an installation on a read-only filesystem refused to start over a documentation file, and the served schema carried the version and bind address of whoever last started the application. It is now held in memory and always describes the running instance
- **Read host and runtime facts when they are requested** — the host name, IPv4 address, platform string, Python build and host boot time were captured once as the application loaded and published as defaults in the API schema, so the reference on the documentation site described the machine that exported it. They are now resolved per request and no longer appear in the schema

### ⚡ Performance

- **Stopped rebuilding the editor configuration on every keystroke** — typing in a project file rebuilt the editor's language mode, autocomplete, search and save shortcut on each character, which told on a large file. The configuration is now built once per opened file

### 🧪 Testing

- **Added a component-test harness to Eventum Studio** — the UI suite runs in jsdom with React Testing Library, so a screen or a control can be mounted and driven from a test instead of only its pure helpers being covered

### 📝 Other Changes

- **Renamed the status of an instance that has not run from Inactive to Idle** — Inactive is the total covering every instance at rest, and the fleet summary already broke it down into finished, failed and idle, so the state carrying the name of its own total now reads Idle. The Instances status filter follows the chips it filters and reads All / Active / Inactive, where Inactive covers finished, failed and idle alike; a link pinned to `status=running` falls back to All
- **Nested the `server.ui` and `server.api` config sections** — the web UI and REST API toggles moved under `server.ui.enabled` and `server.api.enabled`, matching `server.mcp`. The flat `server.ui_enabled` and `server.api_enabled` keys still work but are deprecated, warn at startup and go away in 2.8; mixing a flat key with its nested form is rejected

## 2.6.0 (2026-06-11)

### 🚀 New Features

- **MCP server — connect an AI agent to Eventum** — a built-in [Model Context Protocol](https://modelcontextprotocol.io) server lets an agent (Claude Code, Cursor, Claude Desktop, and others) author, validate, preview, and run generators using its own model; Eventum embeds no LLM. It runs over **stdio** (`eventum mcp`) for local authoring, and as an optional **HTTP service** mounted into the server (`server.mcp.enabled`) for live management behind Basic auth. The agent gets plugin/formatter/sample discovery and secret-name listing, an always-current template-helper reference, the top-level config schema, worked examples, generator file read/write/delete, real-engine `validate`/`preview_timestamps`/`preview_events`, and ready-made prompts for authoring a generator and live ops; over HTTP it also gets `list`/`status`/`start`/`stop`/`register`/`unregister` and scrubbed log reading of running generators. Over HTTP, write tools are disabled by default and gated by `server.mcp.allow_write`; the stdio server is writable for local authoring unless `--read-only` is passed
- **`samples.<name>.where(**conditions)`** — filter sample rows by multiple equality conditions in a single call (AND-combined). Replaces verbose chained `selectattr` and returns a `Sample` that supports further `where`/`pick` calls
- **`pick(default=...)` and `weighted_pick(weight, default=...)`** — return a fallback value when the sample is empty instead of raising; `pick_n` and `weighted_pick_n` return `[]` on empty samples
- **`module.rand.network.ip_v6` family** — generate random IPv6 addresses: `ip_v6()` for the full space, `ip_v6_global()` for global unicast (`2000::/3`), `ip_v6_link_local()` for link-local (`fe80::/10`), `ip_v6_ula()` for unique local (`fc00::/7`)
- **`module.rand.network.mac(oui=..., vendor=...)`** — fix the OUI prefix to a 3-byte string (e.g. `mac(oui="00:50:56")`) or pick one at random from a built-in table for a given vendor (e.g. `mac(vendor="dell")`); 20 vendor keys cover Apple, Cisco, Dell, HP, Intel, VMware, and others. No-argument call keeps the previous fully-random behavior
- **`module.rand.network.ip_v4_private()`** — generate a random RFC 1918 private IPv4 address from any class (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) with realistic weights
- **`module.rand.string.pattern(format_string)`** — build random strings from a printf-like pattern with specifiers `%a %A %l %d %n %h %H %p %w %%` and repeat syntax `{N}` (e.g. `pattern("ORD-%A{3}-%d{6}")`)
- **ClickHouse output: `pool_maxsize` parameter** — configure the HTTP connection pool size toward the ClickHouse host (default `32`); raise it together with `generation.max_concurrency` to avoid `Connection pool is full` warnings and connection churn under bursts of concurrent writes
- **`module.rand.crypto.sha1()`** — generate a random 40-character hex string (SHA-1-length)

### 🐛 Bug Fixes

- **Failed server startup no longer hangs the app** — when the server cannot start (e.g. the port is already in use), `eventum run` now stops the generators and exits with a clear `Server failed to start` error instead of running headless until interrupted; a server that dies after a successful startup now shuts the whole app down instead of leaving it running without a server
- **Dot-separated config keys work at any depth, in every YAML file** — previously only the top level of `eventum.yml` understood dotted keys, so a nested spelling like `server: {mcp.enabled: true}` was rejected with `extra inputs are not permitted`. Now `eventum.yml`, generator configs, `startup.yml`, and time-pattern files all accept dotted keys at any nesting level, both spellings can be mixed and are deep-merged, and defining the same key twice fails with the exact conflicting path

## 2.5.0 (2026-05-14)

### 🚀 New Features

- **Template dispatch API** — templates can route each event across multiple sub-templates with `dispatch.next(...)`, end generation early with `dispatch.exhaust()`, and drop unwanted events with `PluginEventDroppedError`; new `dropped` counter exposed in generator stats, pipeline graph, and metrics modal
- **`module.rand.network.ip_v4_in_subnet(cidr)`** — generate random IPv4 host addresses within a CIDR subnet (handles `/31` per RFC 3021 and excludes network/broadcast for standard subnets)

### 🐛 Bug Fixes

- Fix shutdown hang when log-stream WebSockets stay open — uvicorn now honors `timeout_graceful_shutdown`, and a second termination signal forces exit

## 2.4.0 (2026-04-02)

### 🚀 New Features

- **Scenarios** — compose multiple generator instances into named workflows with shared global state; new Scenarios page with bulk operations and Scenario page with interactive Data Flow diagram
- **Scenarios API** — CRUD endpoints for scenarios, global-state, and globals-usage (existing endpoints preserved for backward compatibility)
- **Instance metrics** — redesigned metrics modal as an interactive pipeline graph
- **Home page** — new home page with action cards and recent projects; Monitoring dashboard moved to a dedicated page
- **State management** — project State tab redesigned as editable key-value tables; CodeMirror JSON editor for value editing

### 🐛 Bug Fixes

- Fix `list_generators` raising `ValueError` when path is not relative to generators directory
- Fix `globals-usage` path parameter conflict

## 2.3.1 (2026-03-24)

### 🐛 Bug Fixes

- Fix Docker image failing to start with `exec /app/.venv/bin/eventum: no such file or directory` — split `uv sync` into two steps so the CLI entry point is created after full source is available

## 2.3.0 (2026-03-03)

### 🚀 New Features

- Add Kafka output plugin — full Apache Kafka integration with SASL auth, SSL/mTLS, compression (gzip/snappy/lz4/zstd), and batching, powered by aiokafka
- Add TCP output plugin — send events over persistent TCP connections with SSL/TLS and auto-reconnect
- Add UDP output plugin — send events as UDP datagrams

### ⚡ Performance

- Migrated to Python 3.14t (free-threaded) for improved concurrency
- Improved core architecture with multithreading for better performance and reliability

### 📦 Dependencies

- Added `aiokafka`
- Removed `aiostream`, `janus`, `lru-dict`, `uvloop`

### 🧪 Testing

- Expanded test coverage with integration and performance tests

### 📝 Other Changes

- Expanded template plugin documentation
- Added blog to the documentation site

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
