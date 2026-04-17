---
paths:
  - "eventum/server/**/*.py"
---

# Server Rules

## Transport only

Domain logic lives in `core/` and `app/`. `server/` only wires HTTP transports - routers and service injectors carry no business rules.

## Services

- A service lives under `services/<name>/` and exposes `inject_service(app, ...)` that mounts it via `app.mount(...)` or `app.include_router(...)`.
- Build-time failures escape this layer only as `ServiceBuildingError` - wrap anything else before raising.
- Import injectors lazily inside the `if enabled_services.get('<name>', False)` branch in `server/main.py` - disabled services must not be imported.
- Adding a service also adds an entry to `EnabledServices` (`server/main.py`) and a flag to `ServerParameters` (`app/models/parameters/server.py`).
