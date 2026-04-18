---
paths:
  - "../content-packs/generators/**/templates/**/*.jinja"
---

# Template Plugin Rules

The template event plugin renders events from Jinja2 templates per timestamp. All existing content-pack generators use it.

## Template files

- Name templates after what they produce: distinct per event type (`syscall-execve.json.jinja`), or plain `event.json.jinja` for a single-event generator.
- Entries under `templates:` use descriptive keys (`access_success`) - aliases that appear in logs, independent of the file path.
- Shared macros live in `templates/macros/*.jinja`, imported via `{% import 'macros/common.jinja' as common %}`.

## Picking modes

Pick `mode` in the template plugin config by pipeline shape:

- `chance` / `any` - random: `chance` weighted by frequencies (e.g. 84% / 11% / 5%), `any` - uniform frequencies.
- `spin` / `chain` - cyclic: `spin` by declaration order, `chain` by user-defined sequence.
- `fsm` - state machine keyed by a state field (login -> activity -> logout).
- `all` - every template renders for each timestamp.

## State discipline

- `shared` - visible to every template in one generator. Main tool for cross-template correlation.
- `locals` - visible only to one template.
- `globals` - shared across generators in the process, thread-safe. Rare in content-packs.
- Cap growing collections (`if len(pool) > 100: pool.pop(0)`) - unbounded state leaks memory.

## Hot path

Templates render every timestamp; per-event work scales linearly with rate.

- `module.rand.*` is the fastest source; use it when it covers the data you need.
- `module.faker.*` / `module.mimesis.*` cover domains `rand` doesn't (names, addresses, products) at higher per-call cost - use them for that coverage.
- Pre-generate into `samples/` when a fixed pool works - cheaper than regenerating per render.
- Prefer direct picks (`module.rand.choice()`) over iteration.

## Distributions and weights

Real data is skewed; uniform picks may produce unrealistic traffic.

- Skewed numerics: `module.rand.number.lognormal` for byte sizes, `exponential` for durations, `gauss` for metrics. Use `integer(a, b)` only when the data is actually uniform.
- Weighted picks: `module.rand.weighted_choice(values, weights)` for status codes, logon types, protocols.
- Template `chance` values approximate real source frequencies (vendor docs, Elastic samples, production ratios).

## Jinja2 gotchas

- `{{ value | tojson }}` embeds any value as JSON - emits outer quotes for strings; don't wrap in `"..."`.

## ECS `event.sequence`

Optional - include only for sources that publish sequence numbers (Windows event log, auditd, some DBs). When present, track a per-host counter in `shared` and increment per render.

## Quick reference

Full docs: ../docs/content/docs/plugins/event/template/

### Context variables

| Variable | Type | Description |
|----------|------|-------------|
| `timestamp` | `datetime` | Timezone-aware datetime of the event. |
| `tags` | `tuple[str, ...]` | Tags from the input plugin. |
| `params` | `dict` | Constants from the `params` config field. |
| `vars` | `dict` | Per-template variables from the `vars` config field. |
| `samples` | `SamplesReader` | Named datasets from `samples`. |
| `locals` | `State` | Per-template state. |
| `shared` | `State` | State shared across templates in one generator. |
| `globals` | `State` | Thread-safe state across all generators. |
| `module` | `ModuleProvider` | Gateway to `rand` / `faker` / `mimesis` and any installed Python package. |
| `dispatch` | `Dispatcher` | Event-flow control (`drop`, `next`, `exhaust`). |
| `subprocess` | `SubprocessRunner` | Execute shell commands. |

### State methods

Docs: ../docs/content/docs/plugins/event/template/state.mdx

All three scopes share one interface. Individual ops on `globals` are thread-safe; wrap compound ops with `acquire` / `release` to make them atomic.

| Method | Signature |
|--------|-----------|
| `get` | `(key, default=None) -> Any` |
| `set` | `(key, value) -> None` |
| `pop` | `(key, default=None) -> Any` |
| `update` | `(mapping: dict) -> None` |
| `clear` | `() -> None` |
| `as_dict` | `() -> dict` |
| `state[key]` | Equivalent to `state.get(key)`. |
| `acquire` / `release` | `() -> None` - `globals` only, for atomic compound ops. |

### Dispatch

Docs: ../docs/content/docs/plugins/event/template/dispatch.mdx

Call any of these from a template to stop rendering immediately with the specified effect.

| Method | Signature | Effect |
|--------|-----------|--------|
| `dispatch.drop` | `() -> Never` | Drop event for this timestamp. |
| `dispatch.next` | `(max_repicks=64) -> Never` | Discard output and re-pick templates. Excess repicks fail with `PluginProduceError`. |
| `dispatch.exhaust` | `() -> Never` | Signal completion; stop the generator. |

### Subprocess

Docs: ../docs/content/docs/plugins/event/template/subprocess.mdx

`subprocess.run(command, cwd=None, env=None, timeout=None) -> SubprocessResult` executes `command` in shell, captures output. Returns `SubprocessResult(stdout: str, stderr: str, exit_code: int)`. Raises `subprocess.TimeoutExpired` on timeout.

### Samples

Docs: ../docs/content/docs/plugins/event/template/samples.mdx

`samples.<name>` returns a `Sample`:

| Method | Signature | Description |
|--------|-----------|-------------|
| `sample.pick` | `() -> Row` | Uniform random row. |
| `sample.pick_n` | `(n) -> list[Row]` | `n` uniform rows with replacement. |
| `sample.weighted_pick` | `(weight_col) -> Row` | Random row weighted by a column. |
| `sample.weighted_pick_n` | `(weight_col, n) -> list[Row]` | `n` weighted rows. |
| `len(sample)` | `-> int` | Number of rows. |
| `sample[i]` | `-> Row` | Row by index. |

`Row` is a tuple with named access when the source has headers or keys: `row.name`, `row.email`, or `row[0]`, `row[1]`.

### Module provider

Docs: ../docs/content/docs/plugins/event/template/modules.mdx

`module[<name>]` resolves first from bundled modules under `eventum.plugins.event.plugins.template.modules`, then falls back to any installed Python package or package from standard library. Imports are cached.

**Bundled: `module.rand`**

Top-level: `shuffle`, `choice`, `choices`, `weighted_choice`, `weighted_choices`, `chance`.

| Namespace | Functions |
|-----------|-----------|
| `module.rand.number` | `integer`, `floating`, `gauss`, `lognormal`, `exponential`, `pareto`, `triangular`, `clamp` |
| `module.rand.string` | `letters`, `letters_lowercase`, `letters_uppercase`, `digits`, `punctuation`, `hex` |
| `module.rand.network` | `ip_v4`, `ip_v4_public`, `ip_v4_private_a`, `ip_v4_private_b`, `ip_v4_private_c`, `ip_v4_in_subnet`, `mac` |
| `module.rand.crypto` | `uuid4`, `md5`, `sha256` |
| `module.rand.datetime` | `timestamp(start, end)` |

**Bundled: `module.faker` / `module.mimesis`**

Locale-keyed: `module.faker.locale['en_US']` returns a `Faker('en_US')`; `module.mimesis.locale['en']` returns `Generic(Locale('en'))`. Locales are cached; unknown ones raise `KeyError`. All Faker / Mimesis methods are available on the returned instance. `module.mimesis` also exposes `.enums` and `.random`.

Full catalogs: [Faker providers](https://faker.readthedocs.io/en/master/providers.html), [Mimesis API](https://mimesis.name/en/master/api.html).

**Dynamic: `module.<package>`**

Any Python package: `module.numpy.array(...)`, etc.

### Jinja2 extensions

`jinja2.ext.do` (inline expressions via `{% do expr %}`) and `jinja2.ext.loopcontrols` (`{% break %}`, `{% continue %}`) are enabled.
