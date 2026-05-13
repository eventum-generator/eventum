---
paths:
  - "eventum/plugins/**/*.py"
---

# Plugin Rules

Common rules for all plugin types. Type-specific plugin contracts live in `.claude/rules/backend/plugins/{input,event,output}.md` and are auto-loaded when working under `eventum/plugins/<type>/`.

## Class hierarchy

- Declaring a plugin as `class Foo<Type>Plugin(<Type>Plugin[ConfigT, ParamsT]):` auto-registers it.
- `ConfigT` should be `Foo<Type>PluginConfig`.
- `ParamsT` should be `<Type>PluginParams`, or a subclass `Foo<Type>PluginParams(<Type>PluginParams)` if the plugin needs extra params.
- `register=False` class kwarg opts out of auto-registration (used only on abstract intermediates).

## Config vs params

- **Config** (`ConfigT`) - user-facing plugin settings declared in `config.py`.
- **Params** (`ParamsT`) - parameters that are injected to plugin for its runtime. Not user-visible.

## Config model

- Inherit the category config: `InputPluginConfig` / `EventPluginConfig` / `OutputPluginConfig`.
- Always `frozen=True, extra='forbid'`.
- Cross-field validation via `@model_validator`.
- Multi-mode configs: `RootModel` + `Field(discriminator=...)`.

## Init

- Override `__init__` with `@override` and call `super().__init__(config=config, params=params)` first.
- `__init__` is for validation and setup - acquiring runtime resources happens in the type-specific lifecycle.
- Resolve relative user paths via `self.resolve_path(cfg_path_field)`.
- Raise `PluginConfigurationError` for problems Pydantic can't catch.

## Directory layout

```
eventum/plugins/<type>/plugins/<name>/
    plugin.py       # plugin class
    config.py       # Pydantic config
    tests/
        test_plugin.py
        static/     # fixtures
```

## Cross-cutting updates

- Any user-facing change - new plugin or config field change - must be mirrored in the UI (Zod schema + form) and docs (MDX page). See `frontend/ui.md` "Plugin UI" and `docs/mdx.md` rules.
