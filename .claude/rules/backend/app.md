---
paths:
  - "eventum/app/**"
---

# App Rules

## Configuration models

Pydantic models under `eventum/app/models/` back user-facing config files: `config/eventum.yml` and `config/startup.yml` (startup params). Any field change MUST be mirrored in:

- the reference file under `config/`
- the matching docs page under `../docs/content/docs/core/config/` (`eventum-yml.mdx`, `startup-yml.mdx`)
