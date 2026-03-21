---
description: Rules for Jinja2 event templates
globs:
  - "**/templates/**/*.jinja"
  - "**/templates/**/*.json.jinja"
---

# Jinja2 Template Rules

## Template Context Variables

Templates receive an `EventContext` with these variables:

| Variable | Type | Description |
|----------|------|-------------|
| `timestamp` | `datetime` | Event timestamp from input plugin |
| `tags` | `tuple[str, ...]` | Tags from input plugin |
| `locals` | `State` | Per-template local state (persists across renders of same template) |
| `shared` | `State` | Shared state across all templates in the same generator |
| `globals` | `State` | Global state across all generators (inter-process) |
| `params` | `dict` | Constant parameters from config `params` field |
| `vars` | `dict` | Per-template variables from config `vars` field |
| `samples` | `dict` | Named samples loaded from config `samples` field |

## Module Functions

Call via `module.<package>.<function>()` syntax in templates:

- `module.rand.*` -- random data generation (integers, floats, choices, UUIDs)
- `module.faker.*` -- Faker-based realistic data
- `module.mimesis.*` -- Mimesis-based realistic data

For external Python packages, use `module.<package>.<function>` -- this is very powerful and avoids the need for custom module implementations.

## Jinja2 Extensions

Templates run with these extensions enabled:
- `jinja2.ext.do` -- expression statements
- `jinja2.ext.loopcontrols` -- `break` / `continue` in loops

## File Conventions

- Extension: `.jinja` (always, validated by config)
- For JSON output: name as `*.json.jinja` to signal intent
- Template paths in config must be relative (never absolute)
- Templates are loaded via `FileSystemLoader` from the generator project directory

## ECS Field Conventions (for content packs)

- Output JSON should follow Elastic Common Schema (ECS) field naming
- Use dot notation for nested fields: `source.ip`, `event.category`
- Timestamps in ISO 8601 format: `{{ timestamp.isoformat() }}`

## State Usage

- `locals` -- use for per-template counters, sequences, state machines
- `shared` -- use for cross-template coordination within a generator
- `globals` -- use sparingly, for inter-generator coordination only
- State objects behave like dicts: `{% set _ = locals.update({'counter': locals.get('counter', 0) + 1}) %}`

## Macros

- Define reusable macros in separate `.jinja` files and import them
- Use `{% import 'macros/common.jinja' as common %}`
