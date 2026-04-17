---
paths:
  - "eventum/core/**"
---

# Core Rules

## Configuration models

- `GenerationParameters` (`eventum/core/parameters.py`) backs the `generation.*` section of the settings tree. Field changes MUST be mirrored in `config/eventum.yml` and `../docs/content/docs/core/config/eventum-yml.mdx`.
- `GeneratorParameters` (`eventum/core/parameters.py`) adds per-generator runtime fields on top of `GenerationParameters`. Any field change here MUST be mirrored in `config/startup.yml` and `../docs/content/docs/core/config/startup-yml.mdx`.
