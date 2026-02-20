# Stage 1: Build app
FROM python:3.13-slim AS app-build

WORKDIR /app/
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
RUN pip install uv

COPY pyproject.toml uv.lock .python-version README.md LICENSE ./
COPY eventum/__init__.py eventum/
RUN uv sync

COPY eventum/ eventum/


# Stage 2: Build React UI
FROM node:24-slim AS ui-build

WORKDIR /app/eventum/ui/
COPY eventum/ui/package*.json ./
RUN npm ci --legacy-peer-deps

COPY eventum/ui/ ./
RUN npm run build


# Stage 3: Assemble final image
FROM python:3.13-slim

WORKDIR /app/
COPY --from=app-build /app/eventum/ /app/eventum/
COPY --from=app-build /app/.venv/ /app/.venv/
COPY --from=ui-build /app/eventum/www/ /app/eventum/www/

COPY config/ /app/config/
RUN mkdir -p /app/logs

EXPOSE 9474

ENTRYPOINT ["/app/.venv/bin/eventum"]
CMD ["run", "-c", "/app/config/eventum.yml"]
