---
name: create-generator
description: Create a new Eventum content pack generator -- orchestrate agents through research, design, build, validate.
user-invokable: true
argument-hint: "<data-source-name> (e.g. linux-auditd, web-nginx, network-dns)"
---

## Create Event Generator

Orchestrate the creation of a new content pack generator for **$ARGUMENTS** by delegating to your team of agents.

### Phase 1: Research

**Delegate to researcher agent**:

- Research the data source thoroughly:
  - Official specification (protocol RFCs, vendor docs, event ID catalogs)
  - Elastic integration from `https://github.com/elastic/integrations/tree/main/packages/<name>`:
    - `data_stream/*/fields/*.yml` -- field definitions
    - `data_stream/*/sample_event.json` -- ground truth for JSON structure
  - Event structure: types, fields, correlations, interdependencies
  - Frequency distributions: real production ratios between event types

- Present research findings to TL:
  - Table of event types with frequencies and ECS categories
  - Key field interdependencies and correlation patterns
  - Proposed architecture (template count, picking mode, shared state strategy)

**TL directly**: Present research findings to the user for approval before proceeding.

### Phase 2: Design

**TL directly**:

Based on researcher's findings, outline the generator architecture:
- Picking mode (chance, fsm, spin, all, chain)
- Host cardinality (single vs multi)
- Template granularity
- Correlation strategy
- Sample data needs

Present to user for approval.

### Phase 3: Build & Validate

**Delegate to generator-builder agent**:

- Create the full generator project at `../content-packs/generators/<name>/`:
  - `generator.yml` -- pipeline config
  - `templates/` -- Jinja2 templates
  - `samples/` -- CSV/JSON sample data
  - `README.md` -- documentation
- Read the API reference at `.claude/skills/create-generator/api-reference.md`
- Read existing generators in `../content-packs/generators/` for patterns
- Follow conventions from `../content-packs/CLAUDE.md`
- Run the full 5-check validation protocol (see generator-builder agent docs):
  1. **Mass rendering** — generate 100,000+ events in sample mode, validate every one
  2. **Conditional branch coverage** — verify all `{% if %}`/`{% else %}` paths fire
  3. **Sample data integrity** — all files exist, non-empty, fields match template usage
  4. **Memory & performance** — no unbounded state growth; optimization suggestions
  5. **Special character safety** — sample data with `"`, `\`, unicode doesn't break JSON

The generator-builder agent builds, validates, reviews, and fixes issues in a single pass — no separate review or QA phase. If validation fails after 3 fix attempts, stop and consult the user.

**Checkpoint**: Present the generator structure, key templates, and validation results to the user before proceeding.

### Phase 4: Add to Hub

**Delegate to docs-writer agent**:

- Create a new generator data file at `../docs/lib/hub-data/generators/<slug>.ts`:
  - Study existing generator files in `../docs/lib/hub-data/generators/` for patterns
  - Follow the `GeneratorMeta` interface from `../docs/lib/hub-types.ts`
  - Fill in all fields: slug, displayName, category, description, dataSource, format, eventCount, templateCount, highlights, generatorId, eventTypes, realismFeatures, parameters, sampleOutputs
  - Pick the right `CategoryId` from `../docs/lib/hub-categories.ts`
  - Write a concise, source-focused description (not "Generates realistic...")
- Add the import and array entry in `../docs/lib/hub-data/index.ts`
- Verify with `cd ../docs && pnpm build`

### Phase 5: Summary

**TL directly**:

Present to the user:
- Generator created and its location
- Event types and distributions
- Validation results (event count, JSON validity, ECS compliance)
- Hub page URL: `/hub/<slug>`

### Phase 6: Improvements

**TL directly**:

Ask the user before creating improvement issues. If approved:
- Check existing issues: `gh issue list --repo eventum-generator/eventum --limit 100 --state open`
- Create issues for template API gaps, UX improvements, or missing features discovered during development

### Important

- Do NOT commit or push unless the user explicitly asks.
- Track progress with the todo list throughout.
- Multiple generator-builder agents can run in parallel for different generators.
- If blocked or uncertain, ask the user rather than guessing.
