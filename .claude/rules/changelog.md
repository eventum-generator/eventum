# Changelog Rules

`CHANGELOG.md` at the repo root is the developer-facing log. Entries accumulate under `## Unreleased`; the release skill renames that heading to `## <version> (YYYY-MM-DD)`. The user-facing page under `../docs/content/docs/changelog/` is a separate artifact - see `docs/mdx.md`.

## Structure

- `###` sections, only those that apply: `🚀 New Features`, `🐛 Bug Fixes`, `⚡ Performance`, `📦 Dependencies`, `🧪 Testing`, `🏗️ Architecture`, `📝 Other Changes`.
- `####` subsections group entries by component - `Eventum Studio`, `Core`, `Plugins`, `API/CLI`, `MCP`, `Other` (the `Component` field of the Task tracker). Pick it from the commit scope: `ui` -> Eventum Studio, `core` / `app` -> Core, `plugins` -> Plugins, `api` / `cli` / `server` -> API/CLI, `mcp` -> MCP.
- Components keep one order across a release, heaviest first. Drop the subsections when a section holds one or two entries.

## Entries

Shape: `- **<what was done>** — <detail>`. Bold lead, em dash, no trailing period.

- The lead names the change in past tense: "Rebuilt Monitoring into a live dashboard". Not the problem - "Monitoring no longer freezes" is a bug report. Earlier behaviour goes in the detail, and only where the change makes no sense without it.
- One entry per user-visible change, ordered by impact, not by merge date. Merge changes to the same screen or mechanism; dense prose, no module names.
- `📝 Other Changes` takes renames, deprecations and moved config keys - a settings key rename is not a feature. Internal-only work gets no entry.
