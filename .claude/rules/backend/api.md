---
paths:
  - "eventum/api/**"
---

# API Development Rules

## Entry point

- `build_api_app()` in `api/main.py` is the single entry point. Do NOT create a module-level `app = FastAPI()`.
- Runtime dependencies (generator manager, settings, instance hooks) live on `app.state.*` and are exposed from `api/dependencies/app.py`.

## Router layout

Each router lives in `api/routers/<resource>/` with:

- `routes.py` - handlers
- `models.py` - request and response Pydantic models
- `dependencies.py` - resource-specific FastAPI dependencies
- `__init__.py` - exports `router` (and `ws_router` when applicable)

HTTP and WebSocket handlers go on separate routers (`router` and `ws_router`). Reason: auth dependencies differ between HTTP and WS, and `generate_asyncapi_schema()` walks `ws_router` specifically.

## Auth and registration

Auth is attached at `include_router()` level, not per-route. Use `HttpAuthDepends` for HTTP and `WebsocketAuthDepends` for WS.

## Route handlers

- `description` and `response_description` are required on every route decorator - they are the OpenAPI source of truth.
- Use `merge_responses()` from `api/utils/response_description.py` when a route has multiple structured error responses.
- Translate domain exceptions at the boundary: catch `ManagingError` (and similar) and raise `HTTPException(status_code, detail=...)`. Domain exceptions must not reach the client.

## WebSocket routes

- Define websocket router as `ws_router`, not the `router`.
- Annotate messages with helpers from `api/utils/websocket_annotations.py` - these drive the generated AsyncAPI schema.
- Raise `WebSocketException` (not `HTTPException`) for auth and validation errors inside WS handlers.
- Any new or changed WS endpoint must keep AsyncAPI schema generation passing - it runs at `build_api_app()` time and blocks app startup on failure.

## OpenAPI export

After any route change: re-export `docs/public/schemas/eventum-openapi.json` and run `pnpm generate-api-docs` in `docs/`. Files under `docs/content/docs/api/**` are auto-generated - never edit them directly.
