# Changelog Rules

`CHANGELOG.md` at the repo root is the developer-facing log. Entries accumulate under `## Unreleased` as work lands; the release skill renames that heading to `## <version> (YYYY-MM-DD)`.

The user-facing changelog page under `../docs/content/docs/changelog/` is a separate artifact with its own voice - see `docs/mdx.md`.

## Structure

````markdown
### 🚀 New Features

#### Eventum Studio

- **Rebuilt Monitoring into a live dashboard** — animated Input → Event → Output flow with per-stage metrics, throughput and failure charts, and CPU, memory, disk and network tiles
````

- `###` sections, only those that apply: `🚀 New Features`, `🐛 Bug Fixes`, `⚡ Performance`, `📦 Dependencies`, `🧪 Testing`, `🏗️ Architecture`, `📝 Other Changes`.
- `####` subsections group entries by component, taken from the `Component` field of the Task tracker project: `Eventum Studio`, `Core`, `Plugins`, `API/CLI`, `MCP`, `Other`. Omit components with no entries; skip the subsections entirely when a section holds one or two entries.
- Pick the component from the conventional-commit scope: `ui` -> Eventum Studio, `core` / `app` -> Core, `plugins` -> Plugins, `api` / `cli` / `server` -> API/CLI, `mcp` -> MCP.
- Components keep the same order in every section of a release, heaviest first.

## Entries

- Shape: `- **<what was done>** — <detail>`. Bold lead, em dash, no trailing period.
- The lead names the change in past tense, from the maintainer's side: "Rebuilt Monitoring into a live dashboard", "Closed streaming connections on graceful shutdown". Not the problem and not the symptom - "Monitoring no longer freezes" is a bug report, not a changelog entry.
- Earlier behaviour belongs in the detail, and only where the change makes no sense without it.
- Order entries within a subsection by impact, not by merge date.
- One entry per user-visible change. Merge changes to the same screen or the same mechanism rather than listing each commit.
- Dense prose, facts only. Name what a user sees or configures; leave module names out.

## What belongs where

- `🚀 New Features` - a capability the user did not have before.
- `🐛 Bug Fixes` - corrected or restored behaviour.
- `📝 Other Changes` - renames, deprecations, moved config keys, and anything else carrying no new capability. A settings key rename is not a feature.
- Internal-only work (refactors, CI, tests with no user-visible effect) gets no entry.
