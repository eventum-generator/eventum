# Generator Rules

Content-packs (`../content-packs/`) is the companion repository shipping ready-to-use generators. A generator is a self-contained project under `generators/<category>-<source>/` producing realistic synthetic events that mimic a real data source.

## Project structure
```
generators/<name>/
    generator.yml
    README.md
```

Additional assets live alongside `generator.yml`, depending on the plugins used:

- **Template** event plugin: `templates/` for Jinja2 files (shared macros nested as `templates/macros/`) and `samples/` for CSV/JSON sample data.
- **Script** event plugin: `scripts/` for the Python files.
- **Replay** event plugin: `samples/` for the source log files.
- **Time patterns** input plugin: `patterns/` for YAML files describing the time distribution of timestamps.

`output/` typically holds generator results (batch runs, debugging, etc.) and is gitignored - it isn't an asset directory.

- Name format: `<category>-<source>` - lowercase, hyphen-separated. Pick `<category>` from the existing set in `generators/` (e.g. `cloud`, `network`, `security`, `windows`, `linux`, `web`). Create a new category only when no existing one reasonably fits.
- Every path inside the generator is relative - the project must remain portable.

## generator.yml

`generator.yml` wires three pipeline stages - `input`, `event`, `output`. A typical file:

```yaml
input:
  - cron:
      expression: "* * * * * *"
      count: 5

event:
  template:
    mode: chance
    params:
      hostname: web-srv-01
      server_name: example.com
    samples:
      urls:
        type: json
        source: samples/${params.locale}_urls.json
      user_agents:
        type: csv
        source: samples/user_agents.csv
        header: true
    templates:
      - access_success:
          template: templates/access-success.json.jinja
          chance: 840
      - access_failure:
          template: templates/access-failure.json.jinja
          chance: 110
      - error_upstream:
          template: templates/error-upstream.json.jinja
          chance: 25

output:
  - file:
      path: output/events.json
      write_mode: overwrite
      formatter:
        format: json
```

A generator from the `content-packs` repo must work out-of-the-box with `eventum generate --path generator.yml --id test --live-mode true`. Its defaults should therefore follow these rules:

- Output results to a local file with an appropriate formatter in an `output/` directory.
- Use a predictable steady-rate input, e.g. `cron` or `timer`.

These defaults apply only to generators shipped within the `content-packs` repo. Outside that scope, any Eventum plugin is fine (e.g. `time_patterns`, broker outputs, etc.).

## Parameterization

- `params` and `secrets` variables hold substitution values inserted into configuration before validation - `params` for regular values, `secrets` for sensitive ones (passwords, tokens, API keys resolved from the Eventum keyring at runtime). Do not confuse `params` with the template event plugin's own `params` field, which just holds template variables.
- Use `${params.*}` / `${secrets.*}` placeholders for values users actually need to override (hosts, URLs, tokens, credentials). Don't parameterize values the user doesn't need to touch - it just bloats the setup with knobs nobody cares about.
- Every required `${params.*}` / `${secrets.*}` must be documented in the generator's README under "Parameters".

## Samples

- All sample data lives under `samples/` as CSV (with headers) or JSON (arrays of objects), whatever its size. Do not inline data in `generator.yml` as `type: items`.
- 50-100 items per sample file is the usual scale (hosts, users, processes).
- Use realistic-looking but clearly fake data: RFC 1918 IPs, generic company names (Contoso, Fabrikam), synthetic usernames. Never real PII.

## Source cardinality

How many instances of the data source emit events shapes the generator design:

- **Multi-source** (workstation agents, auditd, sysmon, EDR, web access, fleet IoT) - pool of dozens of instances; correlations (user session, process tree, `event.sequence`) live per instance.
- **Single-source** (firewall, DNS, LB, proxy, broker) - typically one instance; correlations (flow, session, src/dst pair) span traffic through that instance.

Pick the shape from the real context. Mixing them is also ok.

## ECS fields

Event-like outputs follow ECS. If an Elastic integration exists for the source (check [elastic/integrations](https://github.com/elastic/integrations)), mirror its `sample_event.json` exactly; otherwise infer a reasonable ECS shape. For non-event payloads (e.g. API responses with source-specific fields), keep the native format - don't force ECS onto data that doesn't fit it.

When following ECS:

- Top-level: `@timestamp`, `ecs.version`, `event.*`, `host.*`, `agent.*`.
- Source-specific data under its namespace: `winlog.*`, `auditd.*`, `nginx.*`, `aws.*`, etc.
- `related.*` fields (user, ip, hash, hosts) are always arrays - a single value still ships as `["x"]`.
- `event.sequence` is strictly increasing per host or source.

## README

Required sections:

- Title and one-liner on the data source.
- Event types covered - table of action, frequency, category.
- Parameters - table of `params` with defaults, plus Secrets when present.
- Usage - CLI examples for batch and live mode.
- One complete real JSON event as sample output.
- References to vendor docs and the matching Elastic integration.

The limitations section lists only how the generated data differs from the real source: missing event types or fields, inferred values, synthetic rates, timing and volume differences stated as properties of the data (e.g. "related records are seconds apart, not milliseconds"). It never describes Eventum internals - input plugins, timestamps or ticks, queues, template state, guards, batch or live mechanics, generation speed - nor the validation process (captures, calibrations, statistical tests, review rounds, standard deviations across runs). It is written for the consumer of the data: only properties of what is generated. The same holds for every other section: the README describes the generated data (volume and hour curves, event shares, timing between related records) in data terms, never the mechanism that produces it. Operational notes (how to run a finite window, output overrides) belong in Usage; a single Performance line with generation speed is allowed.
