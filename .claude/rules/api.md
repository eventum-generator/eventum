---
description: Rules for FastAPI API routes and middleware
globs:
  - "eventum/api/**"
---

# API Development Rules

## Router Structure

- Routers live in `eventum/api/routers/<resource>/`.
- Each resource directory contains:
  - `routes.py` - route handlers (async functions)
  - `models.py` - response/request Pydantic models
  - `dependencies.py` - FastAPI dependency injection functions
  - `__init__.py` - router exports
- Separate `ws_router` for WebSocket endpoints.

## Route Handler Conventions

- All route handlers are `async def`.
- Use FastAPI dependency injection (`Annotated[Type, Depends(...)]`) for shared logic.
- App-level dependencies (e.g., `GeneratorManagerDep`, `SettingsDep`) come from `eventum.api.dependencies.app`.
- Always provide `description` and `response_description` in route decorators.
- Use `merge_responses()` from `eventum.api.utils.response_description` for combined response docs.

## FastAPI Patches

**Critical**: FastAPI patches (monkey-patches, middleware, startup hooks) must be active during the request lifecycle, not just at registration time. If a patch modifies request processing, ensure it wraps the actual request handler, not just the route definition.

## OpenAPI Spec

- The OpenAPI spec is exported to `../docs/public/schemas/eventum-openapi.json`.
- After adding/modifying any API route, re-export the spec and run `pnpm generate-api-docs` in `../docs/`.
- The docs site auto-generates API documentation pages from this spec.

## Error Handling

- Use `HTTPException` with appropriate status codes.
- Use `WebSocketException` for WebSocket error cases.
- Catch domain exceptions (e.g., `ManagingError`) and translate to HTTP errors.

## Models

- Response models use standard Pydantic `BaseModel`.
- Use `frozen=True` for immutable response models where appropriate.
- Runtime types (internal API types) live in separate `runtime_types.py` / `api_types.py` files.

## Testing

- API tests live in `eventum/api/tests/`.
- Use `httpx.AsyncClient` with `ASGITransport` for async API testing.
- Test both success paths and error paths (invalid input, missing resources, auth failures).
