---
name: create-generator
description: Create a new Eventum content pack generator -- orchestrate agents through research, design, build, validate, review.
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

### Phase 3: Build

**Delegate to generator-builder agent**:

- Create the full generator project at `../content-packs/generators/<name>/`:
  - `generator.yml` -- pipeline config
  - `templates/` -- Jinja2 templates
  - `samples/` -- CSV/JSON sample data
  - `README.md` -- documentation
- Read the API reference at `.claude/skills/create-generator/api-reference.md`
- Read existing generators in `../content-packs/generators/` for patterns
- Follow conventions from `../content-packs/CLAUDE.md`

**Checkpoint**: Present the generator structure and key templates to the user before proceeding.

### Phase 4: Validate

**Delegate to qa-engineer agent**:

- Run generator validation:
  ```bash
  # Sample mode test
  cd ../content-packs && eventum generate \
    --path generators/<name>/generator.yml \
    --id test --live-mode false -vvvvv

  # JSON validity + ECS field check
  # Live mode smoke test (5 second timeout)
  ```
- Report: event count, JSON validity, ECS field presence, any errors

If validation fails: route findings to **generator-builder** to fix, then re-validate. Loop until all checks pass. If the loop does not converge after 3 cycles, stop and consult the user.

### Phase 5: Review

**Delegate to code-reviewer agent**:

- Review generator quality: template correctness, parameterization, realism, README completeness
- If verdict is **FAIL**: route findings to **generator-builder** to fix, then re-review
- Loop until **PASS**. If the loop does not converge after 3 cycles, stop and consult the user.

### Phase 6: Final Verification

**Delegate to qa-engineer agent**:

- Re-run full generator validation after any fixes from review
- Report all-green status

If any check fails: route to **generator-builder** to fix, then re-verify. If the loop does not converge after 3 cycles, stop and consult the user.

### Phase 7: Add to Hub

**Delegate to docs-writer agent**:

- Create a new generator data file at `../docs/lib/hub-data/generators/<slug>.ts`:
  - Study existing generator files in `../docs/lib/hub-data/generators/` for patterns
  - Follow the `GeneratorMeta` interface from `../docs/lib/hub-types.ts`
  - Fill in all fields: slug, displayName, category, description, dataSource, format, eventCount, templateCount, highlights, generatorId, eventTypes, realismFeatures, parameters, sampleOutputs
  - Pick the right `CategoryId` from `../docs/lib/hub-categories.ts`
  - Write a concise, source-focused description (not "Generates realistic...")
- Add the import and array entry in `../docs/lib/hub-data/index.ts`
- Verify with `cd ../docs && pnpm build`

### Phase 8: Summary

**TL directly**:

Present to the user:
- Generator created and its location
- Event types and distributions
- Validation results (event count, JSON validity, ECS compliance)
- Hub page URL: `/hub/<slug>`

### Phase 9: Improvements

**TL directly**:

Ask the user before creating improvement issues. If approved:
- Check existing issues: `gh issue list --repo eventum-generator/eventum --limit 100 --state open`
- Create issues for template API gaps, UX improvements, or missing features discovered during development

### Important

- Do NOT commit or push unless the user explicitly asks.
- Track progress with the todo list throughout.
- Multiple generator-builder agents can run in parallel for different generators.
- If blocked or uncertain, ask the user rather than guessing.
