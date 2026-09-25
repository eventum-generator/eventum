---
name: create-generator
description: Create a new Eventum content pack generator end-to-end - research the data source, build, validate, self-review, document, present to the user, publish a hub page to the docs site.
---

## Input

- Data source name, e.g. `linux-auditd`, `web-nginx`, `network-dns`.
- Optional user constraints (Decide from research if none provided).

## Output

A validated generator at `../content-packs/generators/<name>/` with background and anomaly modes, a README that explains its anomaly chain, and a hub page PR opened in the docs repo (page goes live on PR merge).

## Reference

- Template plugin rules: `.claude/rules/content/templates.md`.
- Generator rules: `.claude/rules/content/generators.md`.
- Hub rules: `.claude/rules/docs/hub.md`.
- Existing generators for layout conventions only, not architecture: `../content-packs/generators/`.

## Process

Nine phases in order. Phases 4 and 5 can send work back when issues surface. Phase 7 is the only user checkpoint.

### 1. Research

Primary sources:
- Vendor documentation or a complete native raw fixture from a maintained integration for the chosen version and transport. Confirm every modeled event class, field meaning, and timestamp source against vendor material. If neither a complete raw record nor a field-complete format specification exists, stop at the research gate; do not invent a wire format.
- Elastic integration `sample_event.json` + `fields.yml` per data stream when available - reference for ECS structure, not proof of the native wire format. Save the matching sample for phase 4.
- Vendor event ID catalogs and documented timing or frequency behavior. Mark unsupported rate assumptions as synthetic in the README.
- Protocol or format RFCs where applicable (syslog, CEF, etc.).

Before naming a new pack, compare `vendor:product:stream` with existing hub cards, content packs, and open PRs. Treat aliases, rebrands, versions, and CEF/KV/JSON encodings of the same event stream as one source; extend the existing pack instead. For a different stream from the same product, compare event IDs and channels and document why a separate pack is useful.

Exit criterion: a versioned native-format reference for every modeled event class and a field map (path, source, generation strategy) targeting ≥90% coverage of reference fields, with gaps and assumptions listed. A missing native-format reference blocks publication.

### 2. Plan

Architecture options - in `.claude/rules/content/templates.md` and `.claude/rules/content/generators.md`.

- **Picking mode** - which template-plugin mode fits the pipeline shape of the source.
- **Input plugin** - `cron` or `timer` for a steady rate (content-pack convention).
- **State strategy** - where state is needed and at what scope.
- **Source cardinality** - multi-source (many instances, per-instance correlations) vs single-source (one instance, per-flow correlations). Full rule: `generators.md`, section Source cardinality.
- **Sample layout** - which fields come from static samples versus generated live.
- **Template reuse** - whether event types overlap enough to share a template via `vars`.
- **Anomaly chain** - a source-specific, multi-event sequence whose actors, targets and identifiers remain consistent amid ordinary traffic; define its observable steps and a detection idea. A generator must also produce ordinary background events without this sequence.

Do not copy architecture from existing generators - they carry known quality issues. Decisions come from phase 1 facts, not from precedent.

Exit criterion: every architectural choice traceable to a phase 1 fact.

### 3. Build

Generator path: `../content-packs/generators/<name>/`. Conventions: `.claude/rules/content/generators.md` and `.claude/rules/content/templates.md`.

Needed by later phases:
- Native raw examples or a complete format specification, plus a matching `sample_event.json` when available, saved under `generators/<name>/reference/` for phases 4 and 6.
- Template output structure mirrors the reference (phase 4 needs ≥90% field coverage).

Add `event.template.params.anomaly_mode: true` to every new generator. When set to `false`, it must generate ordinary background without the complete anomaly chain. Event types used in the chain should also appear independently in background when the source normally emits them; no event type, fixed actor, or static marker should identify the anomaly by itself. The default `true` mode mixes the chain with background. Keep the chain reconstructible from stable identifiers and plausible timing, using the source's own timestamps as a cadence reference when available. Let chain actors also produce ordinary background events.

Caveat: `generator.yml` has two distinct fields named `params`. Top-level `params` / `secrets` are `${params.x}` / `${secrets.x}` substitutions for user-facing overrides. `event.template.params` is a Jinja map of template-internal constants. Full rule: generators.md, section Parameterization.

Exit criterion: all files in place, generator runnable.

### 4. Validate

Generate in sample mode from `../content-packs/` and verify the output with `anomaly_mode` both `true` and `false`:

```bash
flock -x /tmp/eventum-generator-heavy.lock timeout 3 uv run --project ../eventum eventum generate --path generators/<name>/generator.yml --id test --live-mode false
```

Ground rules:
- `--live-mode false` required; live mode hangs on cron ticks.
- For six-field cron expressions, croniter reads seconds from the sixth field: `* * * * * */30` means every 30 seconds. Verify the generated `@timestamp` spacing and daily event volume, including the input `count`; do not infer cadence from the expression alone.
- `timeout 3` bounds the initial sample run - exit code 124 is expected. For full-chain validation, set finite `input[0].cron.start/end` in a temporary config and require exit code 0. Do not mask other exit codes.
- No verbosity flags during validation; high levels stall validation, low levels add noise.
- If the generator errors or produces no output, re-run with `-v` (CRITICAL) up to `-vvvvv` (DEBUG) for diagnostic logs.
- Use the existing Eventum project environment through `uv run --project ../eventum`; skip package installs.

In anomaly mode, verify at least one complete chain, its shared identifiers, and the actual `@timestamp` span against the detection window stated in the README and any timing visible in the primary source. In background mode, verify the complete chain never appears while the constituent event types still occur independently. Check that a chain-only action, fixed actor, or static marker cannot trivially distinguish anomaly mode from background. Include both modes in the checks below.

Five checks, all must pass:
- **JSON parse** - every output line is valid JSON containing ECS fields `@timestamp`, `event`, `ecs` (when applicable).
- **Field coverage and native fidelity** - at least 90% of reference fields present in generated output; compare `event.original` against the versioned vendor record or specification for each event class. List misses and deviations with reasons.
- **Branch coverage** - every `{% if %}` / `{% elif %}` / `{% else %}` in templates produces at least one event (grep distinguishing field values to confirm).
- **Sample integrity** - sample files referenced in `generator.yml` exist; every column or key accessed in templates exists in samples; strings containing `"`, `\`, or unicode are escaped via `| tojson`.
- **State safety** - every `shared.set` / `locals.set` / `.append` / `.update` has a cap or cleanup. No unbounded growth.

Any failure returns to phase 3 (Build), or to phase 2 (Plan) if the root cause is architectural.

### 5. Self-review

Check against every rule in `.claude/rules/content/templates.md` and `.claude/rules/content/generators.md`. Skill-specific failure modes:

- Picking mode defaulted to `chance` on a source that is actually stateful, sequenced, or otherwise non-random.
- Top-level `params` / `secrets` declared but missing from the README parameters table.
- Coverage gaps accepted without justification in the phase 1 field map, or a modeled native record without a complete primary reference.
- README sample event stale from a pre-rebuild run.
- `anomaly_mode: false` still emits a complete anomaly chain, omits normal examples of its constituent event types, or produces no valid background stream.

If anything triggers: return to phase 3, or to phase 2 if the issue is architectural. Rerun phase 4, then redo this phase. Proceed only when nothing fires.

### 6. Document

Write the generator's README to the spec in `.claude/rules/content/generators.md`, section README. Match the tone and structure of existing READMEs in `../content-packs/generators/`.

Two additions specific to this skill:
- The Sample output event must be a real event copied from `output/events.json` before the cleanup step below. Not a hand-written sample.
- Add a clearly labeled `## Anomaly Chain` section that lists the sequence, linking fields, and possible detections. State that `anomaly_mode` defaults to `true` and that `false` produces only background.
- The README Parameters section documents user-facing knobs in two subsections: **Event Parameters** - the `event.template.params` constants a user edits in-file (hostnames, versions, provider suffixes, ...), listed with defaults; and **Output Parameters** - the top-level `${params}` / `${secrets}` placeholders for pointing output at a backend (e.g. OpenSearch host and credentials), shown as the override pattern while the shipped `generator.yml` keeps file output so it runs out of the box. Internal template logic (inline constants, distribution parameters) is not listed.

After the README is written, delete `output/` and `reference/`. They are test artifacts, not committed.

### 7. Approve

Show the user:

- Location: `../content-packs/generators/<name>/`.
- Event types with distributions and picking mode.
- Coverage: `<covered>/<total>` fields against reference.
- One sample event from generator output.
- All five validation checks with pass/fail status for both modes.
- Any notable omissions or trade-offs.

If the user already authorized commits and hub PRs for this work, proceed to phase 8 without asking again. Otherwise ask only: proceed to publish to the hub? Architecture was gated in phases 2 and 5 - do not re-open it.

**Existing authorization or an explicit ok also authorizes the commit and PR in the docs repo for phase 8** - do not ask for permission again. If changes are requested, return to the relevant phase.

### 8. Publish

Add a hub page in `../docs/` following `.claude/rules/docs/hub.md`. Every new generator supports both modes, so set `generationModes` to `['background', 'anomaly']` and keep `anomalyChain` as a short description based on the README. On hub cards, use muted Lucide `Logs` for background and `ScanEye` for anomaly. The hover and accessible labels are only `Background logs` and `Contains anomaly`; never put the chain description in the tooltip. Existing cards default to background only; SAP HANA is anomaly only. Verify with `pnpm build`.

Workflow:
- In the docs repo, branch off `master` (not `develop`) and target the PR at `master`. Branching from `develop` would sweep unrelated work into the PR. The flow is independent of the eventum release cycle.
- Open the PR after `pnpm build` passes. Do not block phase 9 on merge; record the PR URL and continue.

### 9. Report

Final summary to the user:
- Path to generator: `../content-packs/generators/<name>/`.
- Event types and distributions.
- Coverage percentage.
- Hub page URL (live after the docs PR is merged): `/hub/<name>`.
- Docs-repo PR URL and status.

## Notes

**Parallel generators.** Use a separate content-packs worktree for each generator and a separate docs worktree for hub changes. Research and editing may run in parallel, but serialize resource-intensive Eventum validation and Node.js documentation builds with one shared `flock` lock. Keep sample runs short and remove generated output promptly to avoid WSL OOM.
