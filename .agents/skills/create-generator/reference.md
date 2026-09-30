# Eventum generator reference

Everything a content-pack generator can use, verified against the Eventum source. Read it instead of the code.

## generator.yml

```yaml
input:                      # list; several inputs are merged in time order
  - time_patterns:
      tags: [office]        # optional, on any input; reaches templates as `tags`
      patterns: [patterns/office.yml]
event:
  template:                 # the template event plugin
    mode: chance            # all | any | chance | spin | chain | fsm
    params: {...}           # constants -> `params` in templates
    samples: {...}          # datasets -> `samples` in templates
    templates: [...]        # list of one-key maps: alias -> template config
output:
  - file:
      path: output/events.json
      write_mode: overwrite # append (default) | overwrite
      formatter:
        format: json        # plain | json | json-batch | template | template-batch | syslog | eventum-http-input
```

- Two different `params`: top-level `params` / `secrets` are `${params.x}` / `${secrets.x}` substitutions applied to the config text before validation (CLI `--params '{"x": 1}'`, secrets from the keyring). `event.template.params` is a plain map the templates read; it is not settable from the CLI - a README tells users to edit it in `generator.yml`.
- All paths are relative to the directory of `generator.yml` (templates, samples, patterns, output).
- `file` output: `path`, `write_mode`, `encoding` (utf_8), `separator` (OS line separator), `flush_interval` (1 s), `file_mode` (640).
- `json` formatter parses every rendered event and re-serialises it on one line (`indent: 0`); a render that is not valid JSON is reported and not written. `plain` writes the rendered text as is.

## CLI

```bash
uv run --project <eventum-repo> eventum generate --path <generator.yml> --id <id> [options]
```

| Option | Default | Meaning |
|---|---|---|
| `--live-mode` | `true` | `true`: emit at wall-clock time of each timestamp; `false`: emit everything as fast as possible (batch). |
| `--skip-past` | `true` | Live mode only: drop timestamps before now. |
| `--keep-order` | `false` | Write events strictly in timestamp order (disables concurrent writes). Use in every validation run. |
| `--timezone` | `UTC` | Time zone of the timestamps templates receive. |
| `--params` | `{}` | JSON for top-level `${params.*}` substitution. |
| `--batch.size` / `--batch.delay` | 10000 / 1.0 s | Output batching (live mode writes a batch when either is reached). |
| `-v` ... `-vvvvv` | off | Log level: critical ... debug. Validation runs use `-vvv` and expect an empty log. |

A batch run ends when every input is exhausted, so a finite run needs every input to have an `end` (or a finite `count`/`repeat`/list).

## Input plugins

Every input accepts `tags: [..]`. Timestamps of all inputs are merged in time order; the template sees the tags of the input that produced the timestamp. Inside `time_patterns`, only the tags of the `time_patterns` input count - tags in pattern files are ignored - so give each population (office staff, admins, automation) its own `time_patterns` input.

### Datetime values (`start`, `end`, oscillator bounds)

- ISO datetime with offset: `"2026-09-01T00:00:00+00:00"` or `...Z`. A datetime **without offset is read as the local time of the machine** that runs Eventum (a run on a UTC+3 host shifts it by 3 hours) - always write the offset.
- Keywords `now`, `never` (`never` = far future; not allowed in `linspace.end`).
- Relative: `[+|-]<n>d<n>h<n>m<n>s`, e.g. `+1d12h`, `-30m` (relative to now; oscillator `end` is relative to its `start`).
- A time of day (`"08:00:00"`) = today at that time; human phrases (`"tomorrow 9am"`) are parsed by dateparser.

### time_patterns (the default for content packs)

```yaml
- time_patterns:
    tags: [office]
    patterns: [patterns/office-core.yml, patterns/office-edge.yml]
```

Pattern file:

```yaml
label: office core 08-18 UTC              # required, free text
oscillator:
  period: 1
  unit: days                              # weeks|days|hours|minutes|seconds|milliseconds|microseconds
  start: "2026-01-01T00:00:00+00:00"      # anchor; phase of every period
  end: never
multiplier:
  ratio: 4000                             # timestamps per period (int >= 1)
randomizer:
  deviation: 0.03                         # 0..1
  direction: mixed                        # decrease | increase | mixed
  sampling: 1024                          # size of the factor pool (>= 16)
spreader:
  distribution: uniform                   # uniform | triangular | beta
  parameters: {low: 0.3333, high: 0.75}   # fractions of the period
```

- Per period the count is `int(ratio * factor)`; factors are drawn uniformly from `[1-d, 1]`, `[1, 1+d]` or `[1-d, 1+d]` and reused from a shuffled pool. The mean count is about `ratio - 0.5`.
- The spreader places the timestamps inside the period: `uniform {low, high}` (fractions, `0 <= low < high <= 1`), `triangular {left, mode, right}`, `beta {a, b}` over the whole period.
- An hour-of-day curve = several pattern files with a 1-day period anchored at midnight, each covering a band (`low`/`high` = hour/24). Bands add up. A weekly curve = 7-day period anchored on a Monday, one file per weekday band.
- Live mode (`skip_past`) keeps the phase: periods are counted from `start`, so an anchor at midnight keeps the bands on clock hours.
- For a finite batch window, set `start` to a midnight and `end` to the window end in every pattern file of a test copy; the shipped files keep `end: never`.

### Other inputs

| Plugin | Fields | Behaviour |
|---|---|---|
| `cron` | `expression`, `count` (>0), `start`, `end` | `count` timestamps at every cron tick. Six fields are read by croniter with **seconds last**: `* * * * * */30` = every 30 s. |
| `timer` | `seconds` (>= 0.1), `count` (>=1), `start`, `repeat` | `count` timestamps every `seconds`, `repeat` times (infinite if unset). |
| `linspace` | `start`, `end` (no `never`), `count`, `endpoint` (true) | `count` evenly spaced timestamps. |
| `static` | `count` | `count` timestamps at now. |
| `timestamps` | `source`: list of datetimes or a file of ISO lines | Replays given timestamps (must be sorted). Add `+00:00` - values without offset are the machine's local time. |
| `http` | `port`, `host`, `max_pending_requests` | Timestamps on HTTP requests (interactive); not for content packs. |

## Template event plugin

### Picking modes

| `mode` | Template config | Picks per timestamp |
|---|---|---|
| `all` | `template`, `vars` | Every template, in order; one event each. |
| `any` | `template`, `vars` | One template, uniform. |
| `chance` | `template`, `vars`, `chance` (> 0, relative weight) | One template by weight. |
| `spin` | `template`, `vars` | Next template in declaration order, cycling. |
| `chain` | `template`, `vars`; plugin-level `chain: [alias, ...]` | Next alias of `chain`, cycling. |
| `fsm` | `template`, `vars`, `initial: true` (exactly one), `transitions: [{to, when}]` | Current state; see below. |

`templates` is a list of one-key maps: `- alias: {template: templates/x.json.jinja, ...}`. Template paths are relative and end in `.jinja`; aliases are unique.

**FSM.** The first timestamp renders the initial state. Before every later timestamp the transitions of the current state are checked in order against the context of the previous render (`timestamp` and `tags` of the new timestamp, `locals` of the previously rendered template, `shared`, `globals`); the first true condition moves the state, none keeps it.

Conditions (`<state>.<key>` = `locals.key`, `shared.key` or `globals.key`; the key is one flat state key, not a nested path; a missing or `None` value makes comparisons false):

| Condition | Form |
|---|---|
| compare | `{eq: {shared.k: v}}`, `gt`, `ge`, `lt`, `le` (numbers) |
| length | `{len_eq: {shared.k: n}}`, `len_gt`, `len_ge`, `len_lt`, `len_le` |
| membership | `{contains: {shared.list: v}}` (state value contains v), `{in: {shared.k: [a, b]}}` (state value in list) |
| regex | `{matches: {shared.k: "^re"}}` (`re.match`) |
| key present | `{defined: shared.k}` |
| tags | `{has_tags: tag}` or `{has_tags: [a, b]}` (all present) |
| time | `{before: {hour: 9}}`, `{after: {hour: 18, minute: 30}}` - components `year..microsecond` replace those of the timestamp; `after` is `>=` |
| constant | `{always: null}`, `{never: null}` |
| logic | `{and: [c, c]}`, `{or: [c, c]}` (2+ items), `{not: c}` |

For generators with queues, due times and several populations, `mode: all` with one template that dispatches on `tags` and state is usually simpler than `fsm`.

### Samples

```yaml
samples:
  users: {type: csv, source: samples/users.csv, header: true}   # delimiter ',', quotechar '"'
  hosts: {type: json, source: samples/hosts.json}               # array of objects with the same keys
```

- CSV values are strings; JSON keeps types. Without a header, columns are `_0`, `_1`, ...
- `type: items` (inline list) exists but content packs keep all sample data in files.

| Access | Result |
|---|---|
| `samples.users` | `Sample` (loaded once at start) |
| `.pick()` / `.pick(default)` | Uniform random `Row`; empty sample raises unless a default is given. |
| `.pick_n(n)` | `n` rows with replacement. |
| `.weighted_pick(col)` / `.weighted_pick_n(col, n)` | Weighted by a numeric, non-negative column (cumulative weights cached). |
| `.where(col=value, ...)` | New `Sample` of exact-match rows - builds a copy, O(rows) per call; precompute pools in state instead of calling it per event. |
| `len(s)`, `s[i]`, `s.columns` | Size, row by index, column names. |
| `row.name`, `row[0]` | A `Row` is an immutable tuple with named access. |

### Render context

| Name | Value |
|---|---|
| `timestamp` | Timezone-aware `datetime` of this timestamp (generator time zone). Use it as event time. |
| `tags` | Tuple of tags of the input that produced the timestamp. |
| `params` | `event.template.params`. |
| `vars` | This template's `vars`. |
| `samples` | Datasets. |
| `locals` / `shared` / `globals` | State: per template / per generator / per process. |
| `module` | Python modules (below). |
| `dispatch` | Flow control (below). |
| `subprocess` | Shell runner - not used in content packs. |

### State

`get(key, default=None)`, `set(key, value)`, `pop(key, default=None)`, `update(dict)`, `clear()`, `as_dict()` (shallow copy), `state[key]` (= get).

- `get` returns the stored object itself: mutating a list or dict in place (`{% do q.append(x) %}`) changes the state without `set`.
- State lives for the whole run; every container must stay bounded (fixed key set, cap, or eviction on every path).
- `globals` is shared by every generator in the process and thread-safe per call; wrap compound updates in `globals.acquire()` / `globals.release()`. Content packs rarely need it.

### Dispatch

| Call | Effect |
|---|---|
| `dispatch.drop()` | No event for this timestamp (counted as dropped). |
| `dispatch.next(max_repicks=64)` | Discard output, pick templates again for the same timestamp; more than `max_repicks` repicks is an error. |
| `dispatch.exhaust()` | Stop the event stage (end of data). |

Content packs do not shape the rate with `drop`/`next`: every input timestamp yields an event.

### module

`module.<name>` imports a bundled module first, then any installed or standard-library module, cached: `module.math`, `module.random`, `module.datetime`, `module.heapq`, `module.bisect`, `module.json`, `module.hashlib`, `module.uuid`, `module.ipaddress`, `module.numpy`, ...

**`module.rand`** (fast; prefer it):

| Function | Notes |
|---|---|
| `choice(seq)`, `choices(seq, n)`, `shuffle(seq)` | `shuffle` returns a new list (or str). |
| `weighted_choice(items, weights)` / `weighted_choice({item: w})` | |
| `weighted_choices(items, weights, n)` / `weighted_choices({item: w}, n)` | |
| `chance(p)` | True with probability `p` in 0..1 (not percent). |
| `number.integer(a, b)`, `number.floating(a, b)` | Inclusive. |
| `number.gauss(mu, sigma)`, `number.lognormal(mu, sigma)` | `lognormal` mu/sigma are of the underlying normal: median = `exp(mu)`. |
| `number.exponential(lambd)` | `lambd` = 1 / mean. |
| `number.pareto(alpha, xmin=1.0)`, `number.triangular(low, high, mode)`, `number.clamp(v, lo, hi)` | |
| `string.letters(n)`, `letters_lowercase`, `letters_uppercase`, `digits`, `hex`, `punctuation` | |
| `string.pattern('%A{3}-%d{4}')` | `%a %A %l %d %n %h %H %p %w %%`, `{N}` repeats. |
| `network.ip_v4()`, `ip_v4_public()`, `ip_v4_private()`, `ip_v4_private_a/b/c()`, `ip_v4_in_subnet(cidr)` | |
| `network.ip_v6()`, `ip_v6_global()`, `ip_v6_link_local()`, `ip_v6_ula()` | |
| `network.mac(oui=None, vendor=None)` | `vendor`: apple aruba broadcom cisco dell fortinet hp huawei ibm intel juniper lenovo microsoft mikrotik netgear paloalto samsung tplink ubiquiti vmware. |
| `crypto.uuid4()`, `md5()`, `sha1()`, `sha256()` | Random hex digests. |
| `datetime.timestamp(start, end)` | Random datetime in range. |

**`module.faker.locale['en_US']`** returns a cached `Faker`; **`module.mimesis.locale['en']`** returns a cached mimesis `Generic` (also `module.mimesis.enums`, `module.mimesis.random`). Unknown locales raise. Both are much slower than `rand`; use them for names, addresses and products, or pre-generate into samples.

### Jinja environment

- Extensions: `do` (`{% do list.append(x) %}`) and `loopcontrols` (`{% break %}`, `{% continue %}`).
- Macros: `{% from 'templates/_base.json.jinja' import render with context %}` - paths are relative to the generator root.
- `{{ obj | tojson }}` sorts object keys and escapes `<`, `>`, `&`, `'` as `<`, `>`, `&`, `'`. The JSON is valid and decodes to the original text, but a README sample must be copied from the output, not retyped. Build the native raw line as a string and put it in `event.original`.
- `loop.index0` inside `{% for x in xs if cond %}` counts only the matching items; use a plain loop with an inner `if` when the index must match `xs`.
- Attribute access tries the Python attribute first: `d.pop`, `d.items`, `d.keys`, `d.get`, `d.update` on a dict are methods. Use `d['pop']` for data keys that clash.
- `{%- ... -%}` trims whitespace; a template that renders one JSON object should emit nothing else.
- Integer division `//`, `%`, and `module.math` work as in Python; `range`, `namespace()` are available.
