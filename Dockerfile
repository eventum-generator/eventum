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

# Corepack installs the pnpm version pinned by the packageManager field
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable

WORKDIR /app/eventum/ui/
COPY eventum/ui/package.json eventum/ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY eventum/ui/ ./
RUN pnpm build


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
