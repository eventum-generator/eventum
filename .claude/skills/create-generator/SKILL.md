---
name: create-generator
description: Create a new Eventum content pack generator - delegate to generator-builder agent for end-to-end research, build, and validation.
user-invocable: true
argument-hint: "<data-source-name> (e.g. linux-auditd, web-nginx, network-dns)"
context: fork
---

## Current state
- Existing generators: !`ls ../content-packs/generators/`
- Generator count: !`ls ../content-packs/generators/ | wc -l`

## Create Event Generator

Create a new content pack generator for **$ARGUMENTS**.

### Phase 1: Build & Validate

**Delegate to generator-builder agent**:

Give Jane the data source name and let her handle everything end-to-end: research the data source, design the architecture, build the generator, validate it, and return results. Jane has WebSearch/WebFetch tools and does her own research — no need for a separate researcher agent.

Provide Jane with any user-specified requirements (event types, picking mode preferences, special constraints). If none specified, Jane decides based on her research.

**Checkpoint**: When Jane returns, present to the user:
- Generator location and event types with distributions
- Key design decisions (picking mode, correlation strategy, feature choices)
- Validation results (event count, JSON validity, field coverage)
- Any warnings or trade-offs

Get user approval before proceeding.

### Phase 2: Add to Hub

**Delegate to docs-writer agent**:

- Create a generator data file at `../docs/lib/hub-data/generators/<slug>.ts`:
  - Study existing files in `../docs/lib/hub-data/generators/` for patterns
  - Follow `GeneratorMeta` interface from `../docs/lib/hub-types.ts`
  - Pick `CategoryId` from `../docs/lib/hub-categories.ts`
  - Write a concise, source-focused description
- Add import and array entry in `../docs/lib/hub-data/index.ts`
- Verify with `cd ../docs && pnpm build`

### Phase 3: Summary

**TL directly**:

Present to the user:
- Generator created and its location
- Event types and distributions
- Validation results
- Hub page URL: `/hub/<slug>`

### Important

- Do NOT commit or push unless the user explicitly asks.
- Track progress with the todo list throughout.
- Multiple generator-builder agents can run in parallel for different generators.
- If blocked or uncertain, ask the user rather than guessing.
