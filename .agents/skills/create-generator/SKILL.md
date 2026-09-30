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

- **`reference.md` next to this file** - the complete Eventum API a generator uses: `generator.yml`, CLI, every input plugin with `time_patterns` semantics, template picking modes and FSM conditions, samples, render context, state, dispatch, `module.rand` / faker / mimesis, Jinja gotchas. Read it instead of the Eventum source.
- Template plugin rules: `.claude/rules/content/templates.md`.
- Generator rules: `.claude/rules/content/generators.md`.
- Hub rules: `.claude/rules/docs/hub.md`.
- Chain checks: `../content-packs/tools/` (spec format in `tools/README.md`).
- Existing generators for layout conventions only, not architecture: `../content-packs/generators/`.

## Process

Nine phases in order. Phases 4 and 5 can send work back when issues surface. Phase 7 is the only user checkpoint.

### 1. Research

Primary sources:
- Vendor documentation or a complete native raw fixture from a maintained integration for the chosen version and transport. Confirm every modeled event class, field meaning, and timestamp source against vendor material. If neither a complete raw record nor a field-complete format specification exists, stop at the research gate; do not invent a wire format.
- Elastic integration `sample_event.json` + `fields.yml` per data stream when available - reference for ECS structure, not proof of the native wire format. Save the matching sample for phase 4.
- Vendor event ID catalogs and documented timing or frequency behavior. Mark unsupported rate assumptions as synthetic in the README.
- Protocol or format RFCs where applicable (syslog, CEF, etc.).
- Vendor limits the data must respect: lockout thresholds, session caps, rate limits, retention of names or IDs, counters that only grow.

Before naming a new pack, compare `vendor:product:stream` with existing hub cards, content packs, and open PRs. Treat aliases, rebrands, versions, and CEF/KV/JSON encodings of the same event stream as one source; extend the existing pack instead. For a different stream from the same product, compare event IDs and channels and document why a separate pack is useful.

Exit criterion: a field map (path, source, generation strategy) targeting ≥90% coverage when a reference event exists, with gaps and assumptions listed. Prefer a versioned complete native example. If the vendor publishes none after a bounded search, use its documented format and mark every inferred part and the missing-capture limit in the README and draft PR; move to the next source rather than searching indefinitely.

### 2. Plan

Decide each point from phase 1 facts, not from existing generators (they carry known quality issues). Write the decisions down; phase 4 checks them.

- **Rate and hours** - the input sets the rate: every input timestamp yields exactly one event. Use `time_patterns` inputs with a 1-day period anchored at midnight (weekly: 7 days anchored on a Monday), one pattern file per hour band, randomizer deviation about 0.03. Give each population its own tagged input: people follow a working-day curve with a low night; automation, services and scanners stay flat. State the daily volume and per-hour rates.
- **Population** - actors in `samples/` (CSV with header or JSON), each with a bounded activity weight (a floor and a cap) so every actor appears in every 4-day window. Scale the population to the rate so each actor's own rate is realistic.
- **Dispatcher** - one template (`mode: all`) or a few, driven by a queue in `shared`: on each timestamp emit the earliest due record, otherwise start new activity for an idle actor of the timestamp's population, chosen by weight. Records of one moment (a request and its log lines) ride on consecutive timestamps; keep them adjacent. Use the timestamp as event time.
- **Background** - a normal day, not an incident or a fault: failures a few percent of attempts with a monotone law (one failure more common than two), retries and give-ups, occasional bursts carried by a few busy actors. Every vendor limit from phase 1 holds.
- **Anomaly chain** - a source-specific, multi-event sequence whose actors, targets and identifiers stay consistent amid ordinary traffic; its observable steps, linking fields, window and a detection idea. Model it with the log fields the vendor documents.
- **Chain in background** - every chain step, and every actor and actor pair an episode can use, also occurs in ordinary background, often enough to appear in every 4-day background capture (expected count ≥ 10), and the actor is active at the hours episodes start. Only the complete ordered sequence is absent from background.
- **Recurrence** - `anomaly_interval_hours` (default 24) with this recipe: the first episode starts within min(interval, 24 h); each next one is due one interval after the actual start of the previous one and starts in a window of w = min(interval / 4, 6 h) centred on the due time; start hours (the first one included) are weighted by the square of the actor's hourly activity plus a small floor; missed episodes are not replayed. An eligible actor must always be available in the window. If a finite resource (name pool, free slot, desk hours) cannot serve short intervals, restrict the parameter range (e.g. a minimum or multiples of 24) instead of letting episodes slip.
- **Episode shape** - an episode is ordinary activity of its actor with the chain in it: it respects every cap background respects, uses the actor's usual address and host, looks the same just before and just after as the actor's ordinary activity at that hour (lead-in, spacing, aftermath), leaves every state (counters, locks, open objects, names in use) as an ordinary session would, and never cancels, delays or takes over the actor's ordinary work. Rotate actor and target between episodes.
- **Guard** - background must never complete the chain. Prefer designing background so the full sequence cannot form (cooldowns, caps). If a guard is needed, it acts only on the exact final step within the chain window, changes that step's target or outcome to a normal alternative (never reassigns, defers or drops), fires rarely, and suppresses no noticeable share of an ordinary action. The episode's own rows count in the guard's history, and nothing stays armed after an episode.
- **Bounded state** - every list, dict, heap or queue in `shared`/`locals` has a fixed key set, a cap, or eviction on every path.

Exit criterion: every choice traceable to a phase 1 fact.

### 3. Build

Generator path: `../content-packs/generators/<name>/`. Conventions: `.claude/rules/content/generators.md` and `.claude/rules/content/templates.md`; API in `reference.md`.

Needed by later phases:
- Native raw examples or a complete format specification, plus a matching `sample_event.json` when available, saved under `generators/<name>/reference/` for phases 4 and 6.
- Template output structure mirrors the reference (phase 4 needs ≥90% field coverage).
- A chain spec `../content-packs/tools/specs/<name>.json` (format in `tools/README.md`): the key that links steps, the window, and one `match` per step with `bind`/`eq` for identifiers that change between steps.

`event.template.params.anomaly_mode: true` in every new generator; `false` produces background without the complete chain. `anomaly_interval_hours` is validated in the template (fail on out-of-range values).

Caveat: `generator.yml` has two distinct fields named `params`. Top-level `params` / `secrets` are `${params.x}` / `${secrets.x}` substitutions (settable with `--params`). `event.template.params` is a map read by templates and edited in the file. Full rule: generators.md, section Parameterization.

Reason the logic through before the first run: queue order, due times, what each population does at night, what happens when the window has no eligible actor, what the guard sees. It is cheaper than a rerun.

Exit criterion: all files in place, generator runnable.

### 4. Validate

All commands run from `../content-packs/`. One validation set, run once; after a fix, recheck only the affected statistic. Serialize heavy runs with `flock -x /tmp/eventum-generator-heavy.lock` (or the shared slot script if the workspace has one).

**Test copies.** Copy the generator to `/tmp/eventum-<name>/`, set `start` to a midnight with an explicit offset (`"2026-09-01T00:00:00+00:00"`) and `end` to the window end in every pattern file, and set `anomaly_mode` / `anomaly_interval_hours` in the copy's `generator.yml`. Run from the copy:

```bash
uv run --project ../eventum eventum generate --path /tmp/eventum-<name>/off1/generator.yml --id off1 --live-mode false --keep-order true -vvv 2> off1.log
```

The run must exit 0 and `off1.log` must be empty.

**Set:** 2 captures with `anomaly_mode: false` and 2 with `true`, each 4 days (long enough for ≥ 2 episodes at the default interval), plus 1 `true` capture at a short custom interval (e.g. 6 or 8 h).

Checks:
- **Format** - every line parses as JSON; ECS fields present; `event.original` matches the vendor record or documented format for each event class; ≥90% of available reference fields covered (list misses with reasons).
- **Chains** - `uv run --project ../eventum python tools/quickaccept.py tools/specs/<name>.json --off OFF1 OFF2 --on ON1 ON2`: 0 chains in every off capture, every chain step and chain key present in each off. `tools/allbind_chains.py <spec> <capture>` on each on capture equals the number of episodes. If the spec key is a random ID, check actor and actor-pair presence in off yourself.
- **Recurrence** - episode start gaps within interval ± w/2 at the default and the custom interval; first start within min(interval, 24 h); start hours follow the actor's curve; consecutive episodes rotate actor and target.
- **One event per timestamp** - replay the input timestamps of one capture (or render the same inputs with a template that prints only `{{ timestamp }}`) and compare counts: output / input = 1.
- **Episode vs background** - for the episode actor, compare the 30 minutes before and after episodes with the same actor's ordinary activity at the same hours; compare caps and live-object counts (sessions, open roles, pool usage) between modes; count guard fires in both modes.
- **Bounded state** - a 14-day run shows every container flat over time.
- **Live smoke** - a copy with `end: never` and pattern rates scaled up (×10-×100), `--live-mode true` under `timeout 90`: events arrive at wall-clock time, in order, no catch-up burst, empty log. The shipped rates stay unchanged.
- **Speed** - wall time of a 14-day run; one Performance line in the README.

Delete captures when their numbers are recorded; keep only the capture the README sample comes from until phase 6.

Any failure returns to phase 3 (Build), or to phase 2 (Plan) if the root cause is architectural.

### 5. Self-review

Check against every rule in `.claude/rules/content/templates.md` and `.claude/rules/content/generators.md`. Failure modes reviewers found most often:

- Rate shaped by `dispatch.drop()` / `next()` or a 1-second cron instead of the input; people active around the clock.
- An event type, actor, address or actor pair that occurs only in episodes, or is missing from some 4-day background capture.
- Background that looks like an incident: detections or failures everywhere, one repeated filler action dominating the output.
- A guard that suppresses a noticeable share of an ordinary action, leaves a pile-up just below the chain threshold, or stays armed after an episode and changes the actor's next ordinary action.
- An episode that leaves state behind (lingering task, open role, extra live object), pushes a count past the background cap, or differs from ordinary activity just before or after.
- Recurrence that slips: starts pinned to a clock hour, stuck at night, skipped when no actor is free, or ignoring the interval.
- A vendor limit broken (lockout threshold, session cap, counters that must grow).
- Unbounded state; `loop.index0` in a filtered loop; `rand.chance(15)` with a percent instead of a probability.
- Top-level `params` / `secrets` declared but missing from the README parameters table; README commands that do not run (e.g. `--params` for `event.template.params`).
- Coverage gaps or inferred native fields accepted without justification in the phase 1 field map or README.

If anything triggers: return to phase 3, or to phase 2 if the issue is architectural. Recheck the affected statistic, then redo this phase. Proceed only when nothing fires.

### 6. Document

Write the README to the spec in `.claude/rules/content/generators.md`, section README: data terms only - volumes, hour curves, shares, timing between related records - never inputs, queues, guards or the validation process.

Specific to this skill:
- **Every number is measured.** Before handing over, check each figure in the README against the validation numbers (shares, per-day counts, per-actor ranges, spans, gaps, start hours). A range covers all measured captures; state defaults, not one run.
- **Sample output** is one line copied byte for byte from a validation capture of the default configuration (the JSON output escapes `<`, `>`, `&`, `'` - keep the escapes). Never retype it.
- **`## Anomaly Chain`** lists the sequence, linking fields, recurrence (interval from the actual start, window, start hours, what happens at short intervals), episode variation, what background contains of the chain, and a detection idea. With `anomaly_mode: true` each episode adds its own records, so counts of chain parts are about one per episode higher - say so.
- **Parameters** in two subsections: **Event Parameters** - the `event.template.params` a user edits in `generator.yml`, with defaults and valid ranges; and **Output Parameters** - the top-level `${params}` / `${secrets}` placeholders for pointing output at a backend, shown as the override pattern while the shipped `generator.yml` keeps file output. Name the sample files a user edits for their own actors and hosts, and the pattern files that set volume and hours.
- **Usage** - the live command, and how to run a finite batch window (set `start`/`end` in every pattern file, starting at a midnight with an offset). Every command in the README must run as written.
- **Limitations** - only how the data differs from the real source, e.g. "related records are seconds apart, not milliseconds", "no weekly cycle".

After the README is written, delete `output/` and `reference/`. They are test artifacts, not committed.

### 7. Approve

Show the user:

- Location: `../content-packs/generators/<name>/`.
- Event types with shares, daily volume and hour curve.
- Coverage: `<covered>/<total>` fields against reference.
- One sample event from generator output.
- Validation results: chains off/on and per episode, recurrence gaps, one event per timestamp, episode-vs-background comparison, bounded state, live smoke.
- Any notable omissions or trade-offs.

If the user already authorized commits and hub PRs for this work, proceed to phase 8 without asking again. Otherwise ask only: proceed to publish to the hub? Architecture was gated in phases 2 and 5 - do not re-open it.

**Existing authorization or an explicit ok also authorizes the commit and PR in the docs repo for phase 8** - do not ask for permission again. If changes are requested, return to the relevant phase.

For a batch of generators, one independent review per pack by a fresh agent against phases 2 and 5 replaces the user check of each pack: findings of LOW severity are fixed in the README and published; a MEDIUM is fixed and reviewed again.

### 8. Publish

Add a hub page in `../docs/` following `.claude/rules/docs/hub.md`. Every new generator supports both modes, so set `generationModes` to `['background', 'anomaly']` and keep `anomalyChain` as a short description based on the README. On hub cards, use muted Lucide `Logs` for background and `ScanEye` for anomaly. The hover and accessible labels are only `Background logs` and `Contains anomaly`; never put the chain description in the tooltip. Existing cards default to background only; SAP HANA is anomaly only. Verify with `pnpm build`.

The card is compiled from the README: shares, counts, parameters with exact defaults, recurrence wording and the sample (byte-exact) come from there; card text describes the data only. A claim the card writer cannot confirm goes back into the README first.

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

**Parallel generators.** Use a separate content-packs worktree for each generator and a separate docs worktree for hub changes. Research and editing may run in parallel, but serialize resource-intensive Eventum validation and Node.js documentation builds with one shared `flock` lock. Keep captures under `/tmp`, delete them as soon as their numbers are recorded, and never kill processes by pattern - other agents run the same tools.
