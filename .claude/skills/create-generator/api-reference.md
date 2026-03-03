# Eventum Template API Reference

> This file must stay current with the Eventum template plugin. When new template features are added to the backend, update this file.

## Template Context Variables

| Variable | Type | Scope | Description |
|----------|------|-------|-------------|
| `timestamp` | `datetime` | Built-in | Timezone-aware datetime from input plugin. Use `.isoformat()`, `.strftime()`, `.year`, `.hour`, etc. |
| `tags` | `tuple[str, ...]` | Built-in | Tags from input plugin |
| `params` | `dict` | Config | User-defined constants from `generator.yml` → `event.template.params` |
| `vars` | `dict` | Per-template | Per-template variables from each template's `vars` config. **Allows reusing the same .jinja file with different bindings.** |
| `samples` | `SamplesReader` | Config | Named datasets from `samples` config. Access: `samples.<name>` or `samples['name']` |
| `module` | `ModuleProvider` | Built-in | Gateway to `rand`, `faker`, `mimesis`, and any Python package |
| `shared` | `SingleThreadState` | Per-generator | State shared across ALL templates in same generator |
| `locals` | `SingleThreadState` | Per-template | State local to this specific template only |
| `globals` | `MultiThreadState` | Global | State shared across all generators (thread-safe with RLock) |
| `subprocess` | `SubprocessRunner` | Built-in | Execute shell commands (avoid in hot paths) |

## `module.rand` — Built-in Random Utilities

### Selection

```
module.rand.choice(items)                           → random item from sequence
module.rand.choices(items, n)                       → n random items with replacement
module.rand.weighted_choice(items, weights)          → weighted random (two lists)
module.rand.weighted_choice({item: weight, ...})     → weighted random (dict form)
module.rand.weighted_choices(items, weights, n)      → n weighted random items
module.rand.weighted_choices({item: weight, ...}, n) → n weighted random items (dict form)
module.rand.shuffle(items)                           → shuffled copy (returns str if input is str)
module.rand.chance(probability)                      → True with given probability (0.0–1.0)
```

### Numbers — Statistical Distributions

```
module.rand.number.integer(a, b)                    → random int in [a, b]
module.rand.number.floating(a, b)                   → random float in [a, b]
module.rand.number.gauss(mu, sigma)                 → Gaussian (normal) distribution
module.rand.number.lognormal(mu, sigma)             → log-normal (always positive, right-skewed)
module.rand.number.exponential(lambd)               → exponential (lambd = rate = 1/mean)
module.rand.number.pareto(alpha, xmin=1.0)          → Pareto (heavy-tailed, values ≥ xmin)
module.rand.number.triangular(low, high, mode)      → triangular in [low, high] peaking at mode
module.rand.number.clamp(value, min_val, max_val)   → clamp value to [min_val, max_val]
```

**When to use which distribution:**
- `integer(a, b)` — ports, IDs, flat ranges
- `gauss(mu, sigma)` — metrics clustering around a mean (response times, file sizes)
- `lognormal(mu, sigma)` — always-positive right-skewed (byte counts, durations, latencies)
- `exponential(lambd)` — inter-arrival times, session durations (most short, some very long)
- `pareto(alpha)` — extremely skewed (network traffic: few large flows, many tiny)
- `triangular(low, high, mode)` — bounded with a known peak (CPU usage peaking at 60%)

### Strings

```
module.rand.string.hex(size)                        → random hex (0-9, a-f)
module.rand.string.digits(size)                     → random digit characters
module.rand.string.letters(size)                    → random mixed-case ASCII
module.rand.string.letters_lowercase(size)          → random lowercase ASCII
module.rand.string.letters_uppercase(size)          → random uppercase ASCII
module.rand.string.punctuation(size)                → random ASCII punctuation
```

### Network

```
module.rand.network.ip_v4()                         → random IPv4 (any range)
module.rand.network.ip_v4_public()                  → random public IPv4
module.rand.network.ip_v4_private_a()               → random 10.x.x.x
module.rand.network.ip_v4_private_b()               → random 172.16-31.x.x
module.rand.network.ip_v4_private_c()               → random 192.168.x.x
module.rand.network.mac()                           → random MAC (colon-separated)
```

### Crypto

```
module.rand.crypto.uuid4()                          → UUID v4 string
module.rand.crypto.md5()                            → random 32-char hex
module.rand.crypto.sha256()                         → random 64-char hex
```

### Datetime

```
module.rand.datetime.timestamp(start, end)          → random datetime in [start, end]
```

## Faker and Mimesis Libraries

For generating realistic contextual data beyond what `module.rand.*` offers. **Slower than `module.rand` — use for sample data setup or low-frequency fields, not per-event hot paths.**

Only the most common functions are listed below. For the **full function listing**, check the official documentation:
- **Faker**: https://faker.readthedocs.io/en/master/providers.html
- **Mimesis**: https://mimesis.name/en/master/api.html

### Faker (common functions)

```
module.faker.locale['en_US'].name()                 → "John Smith"
module.faker.locale['en_US'].email()                → "john.smith@example.com"
module.faker.locale['en_US'].user_agent()           → browser User-Agent string
module.faker.locale['en_US'].ipv4()                 → random IPv4
module.faker.locale['en_US'].uri_path()             → random URI path
module.faker.locale['en_US'].file_path()            → random file path
module.faker.locale['en_US'].sentence()             → random sentence
module.faker.locale['en_US'].company()              → "Acme Corp"
module.faker.locale['en_US'].hostname()             → "web-01.example.com"
module.faker.locale['<locale>'].*                   → any Faker provider in any locale
```

### Mimesis (common functions)

```
module.mimesis.locale['en'].person.full_name()      → "John Doe"
module.mimesis.locale['en'].internet.ip_v4()        → random IPv4
module.mimesis.locale['en'].internet.url()          → random URL
module.mimesis.locale['en'].file.file_name()        → random filename
module.mimesis.locale['<locale>'].*                 → any Mimesis provider in any locale
module.mimesis.spec['usa'].ssn()                    → country-specific provider
module.mimesis.enums.*                              → enums (Gender, FileType, TLDType, etc.)
```

## Any Python Module

If the name isn't `rand`, `faker`, or `mimesis`, the `module` object imports from Python stdlib or installed packages. Modules are imported once and cached.

```
module.json.dumps(data)                             → serialize to JSON string
module.json.loads(string)                           → parse JSON string
module.math.ceil(value)                             → ceiling
module.hashlib.sha1(b'data').digest()               → SHA1 hash bytes
module.hashlib.sha256(b'data').hexdigest()          → SHA256 hex string
module.base64.b64encode(b'data').decode()           → Base64 encode
module.datetime.timedelta(seconds=30)               → duration object
module.ipaddress.ip_network('10.0.0.0/8')           → IP network object
module.urllib.parse.quote(string)                    → URL-encode
```

## Samples System

### Configuration (3 types)

```yaml
samples:
  # Type 1: Direct items
  statuses:
    type: items
    source: [active, inactive, pending]

  # Type 2: CSV file
  users:
    type: csv
    source: samples/users.csv
    header: true
    delimiter: ','
    quotechar: '"'

  # Type 3: JSON file
  processes:
    type: json
    source: samples/processes.json
```

### Access Methods

```
samples.<name>.pick()                               → random row (uniform)
samples.<name>.pick_n(n)                            → n random rows with replacement
samples.<name>.weighted_pick('weight_column')        → weighted by named column
samples.<name>.weighted_pick_n('weight_column', n)   → n weighted rows
```

### Row Access

```jinja
{%- set row = samples.users.pick() -%}
{{ row.username }}        {# Named access (CSV with header / JSON with keys) #}
{{ row[0] }}              {# Index access #}
```

### Jinja2 Filter Access (also works)

```jinja
{{ samples.users | random }}                {# uniform random #}
{{ (samples.users | random).username }}      {# field from random row #}
```

**Prefer `.pick()` and `.weighted_pick()` over manual filtering loops** — they are built-in and optimized.

## State Management

All three scopes (`locals`, `shared`, `globals`) share the same API:

```
.get(key, default=None)   → get value or default
.set(key, value)          → set value
.update(mapping)          → set multiple values from dict
.clear()                  → clear all state
.as_dict()                → shallow copy of entire state
[key]                     → bracket access (same as get)
```

`globals`-only (for thread safety across generators):

```
.acquire()                → acquire RLock
.release()                → release RLock
```

## Template Picking Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `chance` | Weighted probability per template | Independent events with frequency distribution |
| `any` | Uniform random selection | Equal-probability event types |
| `all` | Every template renders per timestamp | Multi-event sources (one timestamp → N events) |
| `spin` | Round-robin cycling | Deterministic sequences |
| `chain` | Fixed-order sequence per timestamp | Ordered event batches |
| `fsm` | Finite state machine with transitions | Stateful sessions (login→activity→logout) |

### FSM Conditions (for transitions)

```yaml
# Comparison: eq, gt, ge, lt, le, matches (regex)
- to: active
  when:
    gt: { shared.request_count: 0 }

# Length: len_eq, len_gt, len_ge, len_lt, len_le
- to: flush
  when:
    len_gt: { shared.buffer: 100 }

# Membership: contains, in
- to: error_state
  when:
    in: { shared.status: ["error", "fatal"] }

# Timestamp: before, after (components: year, month, day, hour, minute, second)
- to: peak
  when:
    after: { hour: 9 }

# State: defined, has_tags, always, never
- to: tagged_handler
  when:
    has_tags: [critical, security]

# Logic: and, or, not (composable, nestable)
- to: escalate
  when:
    and:
      - gt: { shared.fail_count: 3 }
      - or:
          - has_tags: production
          - gt: { shared.severity: 8 }
```

### Per-Template Variables (`vars`)

Allows reusing the same `.jinja` file with different bindings:

```yaml
templates:
  - info_log:
      template: templates/log-entry.json.jinja
      vars:
        level: INFO
        severity: 1
      chance: 70
  - error_log:
      template: templates/log-entry.json.jinja
      vars:
        level: ERROR
        severity: 3
      chance: 10
```

In template: `{{ vars.level }}`, `{{ vars.severity }}`

## Jinja2 Extensions

Two extensions are always loaded:

| Extension | Feature | Example |
|-----------|---------|---------|
| `jinja2.ext.do` | Expression statements without output | `{% do shared.set('count', 0) %}` |
| `jinja2.ext.loopcontrols` | `break` and `continue` in loops | `{% for u in users %}{% if u.skip %}{% continue %}{% endif %}{% endfor %}` |

## Jinja2 Essentials

```jinja
{%- ... -%}                     whitespace-stripping tags (use on logic lines)
{% do list.append(item) %}      mutate lists in-place
{{ value | tojson }}            serialize to JSON
{{ value | upper }}             uppercase
{{ list | length }}             length
{{ list | random }}             random element
{{ list | sort }}               sorted copy
{{ list | join(', ') }}         join with separator
{{ list | selectattr('key', 'equalto', val) | list }}   filter by attribute
```
