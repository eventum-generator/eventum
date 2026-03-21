---
description: Rules for plugin development (input, event, output plugins)
globs:
  - "eventum/plugins/**"
---

# Plugin Development Rules

## Class Hierarchy

Every plugin follows this inheritance chain:

```
Plugin[ConfigT, ParamsT] (base, register=False)
  -> InputPlugin / EventPlugin / OutputPlugin (category base, register=False)
    -> ConcretePlugin (leaf, auto-registered)
```

- Leaf plugins are auto-registered via `__init_subclass__`. Do NOT manually register.
- Pass `register=False` only on abstract intermediate classes.
- Generic params: `ConfigT` (Pydantic config model), `ParamsT` (TypedDict params).

## Config Models

- Inherit from the category base config (`EventPluginConfig`, `InputPluginConfig`, `OutputPluginConfig`).
- Always use `frozen=True, extra='forbid'` on Pydantic models.
- Use `StrEnum` for string enumerations.
- Discriminated unions via `RootModel` with `Field(discriminator='...')` for configs with multiple modes.
- Use `field_validator` / `model_validator` for cross-field validation.
- `Path` fields that reference user files must be relative (validated explicitly).

## Plugin Params

- Plugin params are `TypedDict` subclasses (not Pydantic models).
- Use `NotRequired` for optional fields, `Required` for mandatory ones.
- Params carry runtime dependencies (loaders, paths) -- NOT config values.

## Init Pre-computation

- Override `__init__` with `@override` decorator.
- Pre-compute everything possible at init time (compile templates, build lookup tables, load samples).
- Use O(1) lookups at produce time -- never O(n) scans in hot paths.
- Raise `PluginConfigurationError` for invalid config detected at init.

## Produce Method

- `produce()` takes a typed params dict -- never separate keyword args.
- Raise `PluginProduceError` for runtime failures during event production.
- Return `list[str]` from event plugins (one string per event).

## Error Handling

- `PluginConfigurationError` -- raised at init for config problems.
- `PluginProduceError` -- raised at produce time for runtime failures.
- `PluginRegistrationError` -- raised for registration conflicts.
- Use `shorten_traceback()` from `eventum.utils.traceback_utils` for user-facing errors.

## Module Functions (Template Plugin)

- Template modules live in `eventum/plugins/event/plugins/template/modules/`.
- Each module exposes functions callable from Jinja2 templates via `module.<package>.<function>`.
- Available built-in modules: `rand`, `faker`, `mimesis`.
- Every new module function needs: implementation + tests + `globals.ts` autocomplete entry + docs update.

## Directory Layout

```
eventum/plugins/<type>/plugins/<name>/
    __init__.py
    plugin.py       # Plugin class
    config.py       # Pydantic config model(s)
    tests/
        __init__.py
        test_plugin.py
        static/     # Test fixtures
```

## Checklist for New Plugins

- [ ] Plugin class inheriting correct category base
- [ ] Pydantic config model (frozen, extra=forbid)
- [ ] Tests in co-located `tests/` directory
- [ ] Zod schema in UI (`ui/src/api/routes/generator-configs/schemas/plugins/<type>/configs/`)
- [ ] UI union index updated (`ui/src/api/routes/generator-configs/schemas/plugins/<type>/index.ts`)
- [ ] UI form component
- [ ] UI registry entry (label, icon, description, default config)
- [ ] MDX documentation page + `meta.json` nav entry
