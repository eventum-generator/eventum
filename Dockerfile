# Stage 1: Build app
FROM python:3.14-slim AS app-build

WORKDIR /app/
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
RUN pip install uv

COPY pyproject.toml uv.lock .python-version README.md LICENSE ./
RUN uv sync --no-install-project

COPY eventum/ eventum/
RUN uv sync


# Stage 2: Build React UI
FROM node:24-slim AS ui-build

WORKDIR /app/eventum/ui/
COPY eventum/ui/package*.json ./
RUN npm ci --legacy-peer-deps

COPY eventum/ui/ ./
RUN npm run build


# Stage 3: Assemble final image
FROM python:3.14-slim

WORKDIR /app/
COPY --from=app-build /app/eventum/ /app/eventum/
COPY --from=app-build /app/.venv/ /app/.venv/
COPY --from=app-build /root/.local/share/uv/python/ /root/.local/share/uv/python/
COPY --from=ui-build /app/eventum/www/ /app/eventum/www/

COPY config/ /app/config/
RUN mkdir -p /app/logs

EXPOSE 9474

ENTRYPOINT ["/app/.venv/bin/eventum"]
CMD ["run", "-c", "/app/config/eventum.yml"]
