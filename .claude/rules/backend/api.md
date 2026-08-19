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
- Translate domain types at the boundary too: a body or a response is annotated with a model from `models.py`, never with a `TypedDict` or dataclass owned by `core/` or the plugins. Sharing one type makes the published schema hostage to a domain contract - and a runtime field added there breaks app startup.

## WebSocket routes

- Define websocket router as `ws_router`, not the `router`.
- Annotate messages with helpers from `api/utils/websocket_annotations.py` - these drive the generated AsyncAPI schema.
- Raise `WebSocketException` (not `HTTPException`) for auth and validation errors inside WS handlers.
- Any new or changed WS endpoint must keep AsyncAPI schema generation passing - it runs at `build_api_app()` time and blocks app startup on failure.

## OpenAPI export

`../docs/public/schemas/eventum-openapi.json` is the schema the documentation site renders its API reference from. It is a committed file that changes only when someone exports it, so it drifts from the code silently.

Export it after any change that the schema carries - a route, its request or response models, its descriptions, or a plugin config model - and again at release time, so the published reference names the released version. `info.version` comes from the package version: at release time export after the version bump, never before.

Take the schema from a running instance; the endpoint needs no authentication:

```bash
uv run eventum run -c <eventum.yml>
curl -s http://<host>:<port>/api/openapi.json \
    | uv run python -m json.tool --indent 4 \
    > ../docs/public/schemas/eventum-openapi.json
```

Then regenerate the reference pages in `../docs`:

```bash
pnpm generate-api-docs
```

The schema and the pages both live in the docs repository, so they ship in a branch and PR of that repository. Files under `docs/content/docs/api/**` are auto-generated - never edit them directly.
