# Eventum Improvement Proposals

Feedback gathered from building content-pack generators (linux-auditd, windows-security, etc.) using the template engine and generator.yml pipeline.

---

## 1. Template API: Missing `module.rand.network.ip_v4_private()` (any range)

**Problem**: When generating network events, you often need "some private IP" regardless of class. Currently you must pick between `ip_v4_private_a()`, `ip_v4_private_b()`, or `ip_v4_private_c()` — which forces the generator author to hardcode a subnet class or add a weighted choice between three functions.

**Proposal**: Add a generic `module.rand.network.ip_v4_private()` that randomly picks from any RFC 1918 range with realistic weights (most traffic is /24 class C).

---

## 2. Template API: No `module.rand.network.port()` helpers

**Problem**: Generating realistic port numbers requires manual `module.rand.number.integer(49152, 65535)` for ephemeral ports or hardcoded weighted choices for well-known ports. Every generator repeats this logic.

**Proposal**: Add convenience helpers:
- `module.rand.network.ephemeral_port()` → random port in 49152–65535
- `module.rand.network.well_known_port()` → weighted random from common ports (80, 443, 22, 53, etc.)

---

## 3. Shared state: No atomic increment / counter primitive

**Problem**: Every single template starts with `shared.get('sequence', 1000)` and ends with `shared.set('sequence', seq + 1)`. This is a very common pattern (monotonic record IDs, sequence numbers) but requires 2 lines of boilerplate in every template.

**Proposal**: Add `shared.increment('key', default=0, step=1)` that atomically gets and increments. Returns the pre-increment value. Saves 2 lines per template and eliminates the possibility of forgetting the final `shared.set()`.

---

## 4. Shared state: No built-in queue/pool abstraction

**Problem**: The correlation pattern (producer appends to a list, consumer pops from it, cap the list, fallback when empty) is repeated verbatim across every correlated event pair. In the linux-auditd generator alone, this pattern appears 6 times across auth_sessions, cred_sessions, and running_services pools. It's easy to get wrong — the validation caught a bug where one template peeked (`list[0]`) instead of consuming (`list.pop(0)`).

**Proposal**: Add a built-in pool/queue primitive:
```
shared.pool('sessions').push(item)           # append + auto-cap
shared.pool('sessions').pop()                # pop(0) or None
shared.pool('sessions').peek()               # read without consuming
shared.pool('sessions', max_size=50)         # set cap on first use
```

This would eliminate ~10 lines of boilerplate per correlated event pair and prevent the peek-vs-pop bug class entirely.

---

## 5. Samples: No way to pick a random row and keep it as a flat dict

**Problem**: CSV samples accessed as `(samples.usernames | random)` return a row object. When you need multiple fields from the same row, you must store the whole row first (`{%- set u = samples.usernames | random -%}`) and then access fields individually. This is fine, but there's no way to destructure or spread a sample row into the template namespace.

**Proposal**: Consider a `| spread` or `| unpack` Jinja2 filter that sets multiple variables from a dict at once — or document the recommended pattern more prominently.

---

## 6. Generator.yml: No way to express correlated template groups

**Problem**: In auditd, the PAM login flow is always: USER_AUTH → CRED_ACQ → USER_LOGIN → (session) → CRED_DISP. With `chance` mode, these events fire independently at their own rates, so the correlation pools may drain or overflow depending on timing. The shared state pool pattern is a workaround, not a first-class solution.

**Proposal**: Consider a `group` or `sequence` picking mode where a single trigger fires a deterministic sequence of templates in order:
```yaml
templates:
  - login_flow:
      mode: sequence
      chance: 80
      steps:
        - templates/user-auth.json.jinja
        - templates/cred-acq.json.jinja
        - templates/user-login.json.jinja
```
This would guarantee correct ordering and eliminate the need for inter-template correlation pools for tightly-coupled event sequences.

---

## 7. Template API: No `timestamp` formatting helpers

**Problem**: The `timestamp.isoformat()` method works for `@timestamp`, but auditd's raw `msg=audit(epoch:serial)` format requires `timestamp.timestamp()`. Other formats (syslog's `MMM dd HH:MM:SS`, Apache's `[dd/Mon/yyyy:HH:mm:ss +0000]`) need `strftime()`. Each generator reinvents timestamp formatting.

**Proposal**: Add built-in timestamp format helpers or document common patterns:
- `timestamp.epoch()` → Unix epoch (float)
- `timestamp.syslog()` → `Feb 21 12:00:01` format
- `timestamp.apache()` → `[21/Feb/2026:12:00:01 +0000]` format

---

## 8. Samples: No support for weighted sampling

**Problem**: When picking from sample data, `| random` gives uniform distribution. But in reality, some entries should be picked more often (e.g., `sshd` appears in 40% of auth events, `cron` in 15%). The workaround is `module.rand.weighted_choice()` with hardcoded lists, which bypasses the sample data entirely.

**Proposal**: Support an optional `weight` column in CSV samples or a `weight` field in JSON samples, then provide a `| weighted_random` filter:
```
{%- set u = samples.usernames | weighted_random -%}
```

---

## 9. Template debugging: No dry-run or single-event mode

**Problem**: When developing a new template, you iterate by running `eventum generate --live-mode` and eyeballing stdout. There's no way to render a single template once with fixed inputs to verify the JSON output. If a template has a Jinja2 syntax error, the error message points to the rendered output line, not the source template line.

**Proposal**: Add a `eventum render --template <path> --params <yaml>` command that renders a single template once with given params and prints the result. Include source-mapped error messages that point to the `.json.jinja` line number.

---

## 10. Generator.yml: `count` in input doesn't scale with template count

**Problem**: `count: 5` means 5 events per second total, distributed across all templates by chance weight. When you add more event types, you may want to increase the count proportionally. There's no way to say "I want ~2 SYSCALL events per second and ~1 auth event per second" without manual weight math.

**Proposal**: Consider supporting per-template rate targets in addition to global count, or document the relationship between `count`, `chance` weights, and expected per-type throughput more clearly.

---

## 11. Template composition: Document and promote `{% include %}` for reducing boilerplate

**Context**: Building the `network-dns` generator (Packetbeat DNS transactions).

**Problem**: The network-dns generator has 10 templates (one per DNS query type: A, AAAA, PTR, CNAME, MX, TXT, SRV, NS, SOA, HTTPS). Each template is ~130 lines, but ~100 lines are identical boilerplate — the `agent`, `client`, `destination`, `ecs`, `event`, `host`, `network`, `network_traffic`, `server`, `source` blocks are the same across all 10. Only `dns.question.type`, `dns.answers`, and a few fields differ per template.

This means ~1000 lines of duplicated JSON across the generator. Any structural change (e.g., adding a new ECS field) requires editing all 10 files identically.

Eventum already uses `FileSystemLoader`, so Jinja2's `{% include %}` and `{% extends %}` are technically available. However:

- They're not documented in the template API reference
- There's no established convention for partial/fragment files
- Variable scoping across includes is subtle (included templates share the caller's scope, but `{% extends %}` blocks have different rules)

**Proposal**: Officially support and document template composition:

1. **Document `{% include %}`** in the template API docs with an example showing shared fragments:

   ```text
   templates/
     _base.json.jinja           # shared ECS boilerplate (convention: _ prefix)
     a-query.json.jinja          # {% include '_partials/agent.json.jinja' %}
   ```

2. **Consider adding a `base_template` config option** in generator.yml that defines a shared skeleton with `{% block %}` markers:

   ```yaml
   templates:
     base: templates/_base.json.jinja
     entries:
       - a_query:
           template: templates/a-query.json.jinja
           chance: 300
   ```

   Where `_base.json.jinja` uses `{% block dns_answers %}{% endblock %}` and each template uses `{% extends base %}`.

3. **At minimum**, add a "Reducing Boilerplate" section to the docs showing how to use `{% include %}` with file-relative paths, since this is the single biggest pain point for generators with many similar templates.

---

## 12. Template API: Missing `module.rand.network.ip_v6()` generator

**Context**: Building AAAA query templates for the DNS generator.

**Problem**: `module.rand.network` has `ip_v4()`, `ip_v4_private_a/b/c()`, `ip_v4_public()`, and `mac()` — but no IPv6 generator. For AAAA DNS queries, I had to manually construct IPv6 addresses:

```jinja2
{%- set ipv6_parts = [] -%}
{%- for i in range(8) -%}
  {%- do ipv6_parts.append(module.rand.string.hex(4)) -%}
{%- endfor -%}
{%- set answer_ip = ipv6_parts | join(":") -%}
```

This is 5 lines of boilerplate for something that should be a single function call. It also produces uncompressed addresses (no `::` shorthand) which looks unnatural.

**Proposal**: Add IPv6 helpers to `module.rand.network`:

- `ip_v6()` → random full IPv6 address (e.g., `2001:db8:85a3::8a2e:370:7334`)
- `ip_v6_global()` → random global unicast IPv6 (2000::/3 range)
- `ip_v6_link_local()` → random link-local IPv6 (fe80::/10)
- `ip_v6_ula()` → random unique local address (fc00::/7, the IPv6 equivalent of RFC 1918)

Python's `ipaddress.IPv6Address` already supports compressed representation, so the output would be realistic.

---

## 13. Template API: Missing `module.rand.network.ip_v4_in_subnet(cidr)` for targeted IP generation

**Context**: Building network DNS templates where clients and servers should be in consistent subnets.

**Problem**: Network generators need IPs within specific subnets. For example, DNS clients should come from `192.168.1.0/24` while DNS servers are on `10.0.0.0/24`. Currently, the only options are:

- `ip_v4_private_c()` → random 192.168.x.x (too broad, different /16 every time)
- `module.rand.number.integer()` to manually compute octets (verbose, error-prone)

There's no way to say "give me a random IP in 10.0.1.0/24" without raw Python arithmetic.

**Proposal**: Add `module.rand.network.ip_v4_in_subnet(cidr: str) -> str`:

```jinja2
{%- set client_ip = module.rand.network.ip_v4_in_subnet("192.168.1.0/24") -%}
{%- set server_ip = module.rand.network.ip_v4_in_subnet("10.0.0.0/28") -%}
```

Implementation would use `ipaddress.IPv4Network(cidr)` to compute the address range, then pick a random host address. This is ~5 lines of Python using the existing `ipaddress` import already in `rand.py`.

---

## 14. Template API: Missing `module.rand.network.community_id()` for Elastic network events

**Context**: Building ECS-compatible network events (DNS, firewall, IDS) that need Elastic's Community ID flow hash.

**Problem**: Every Packetbeat/Elastic network event includes a `network.community_id` field — a standardized hash of the flow 5-tuple (src_ip, src_port, dst_ip, dst_port, protocol). In the DNS generator, I had to inline this computation:

```jinja2
{%- set _cid = module.hashlib.sha1((src_ip ~ ":" ~ src_port ~ ">" ~ dns_server ~ ":53").encode()).digest() -%}
{%- set community_id = "1:" ~ module.base64.b64encode(_cid).decode() -%}
```

This is fragile (relies on Python string methods in Jinja2), doesn't implement the real Community ID v1 spec (which has specific byte packing), and will be duplicated in every network-type generator (DNS, firewall, IDS, netflow, etc.).

**Proposal**: Add `module.rand.network.community_id(src_ip, src_port, dst_ip, dst_port, protocol)` that implements the [Community ID v1 spec](https://github.com/corelight/community-id-spec). The `protocol` parameter would accept IANA numbers (6=TCP, 17=UDP) or string names ("tcp", "udp").

```jinja2
{%- set cid = module.rand.network.community_id(src_ip, src_port, dns_server, 53, "udp") -%}
```

This would be a one-liner instead of a multi-line hash computation, and it would produce spec-compliant output instead of an approximation.

---

## 15. Template output: No JSON validation or structured output mode

**Context**: Building 10 DNS templates with conditional JSON blocks.

**Problem**: Templates produce raw text that must be valid JSON. Conditional fields (e.g., `dns.resolved_ip` only present for A/AAAA queries, `dns.question.subdomain` only when non-empty) require careful comma management around `{% if %}` blocks. A single misplaced comma — invisible in a 130-line template — produces invalid JSON that only fails at runtime.

Example of the fragile pattern:
```jinja2
        "question": {
            "class": "IN",
            "name": "{{ query_name }}",
            "registered_domain": "{{ registered_domain }}",
{% if subdomain %}
            "subdomain": "{{ subdomain }}",
{% endif %}
            "top_level_domain": "{{ tld }}",
            "type": "A"
        },
```

If `subdomain` is false, this produces two consecutive commas only if a human accidentally puts the comma in the wrong place. Getting this right across 10 templates requires careful auditing of every `{% if %}` boundary.

**Proposal**: Add a `format: json` option to the template plugin config that post-processes template output:

```yaml
event:
  template:
    format: json          # Validate and normalize output
    mode: chance
    templates: [...]
```

When `format: json` is set:

1. Parse each rendered template output as JSON (fail fast with a clear error pointing to the template alias, not a raw parse error)
2. Strip trailing commas (the #1 source of template JSON bugs)
3. Optionally compact or pretty-print

This would eliminate the entire class of "conditional comma" bugs that plague every generator with optional fields.

---

## 16. Template API: Timestamp arithmetic helper

**Context**: Building Packetbeat DNS events that have `event.start`, `event.end`, and `event.duration`.

**Problem**: Packetbeat events include `event.start` (when the query was sent) and `event.end` (when the response arrived), with `event.duration` in nanoseconds. Computing the end timestamp from a duration requires:

```jinja2
{%- set duration_ns = module.rand.number.integer(1000000, 80000000) -%}
{%- set duration_td = module.datetime.timedelta(microseconds=duration_ns // 1000) -%}
{%- set end_ts = timestamp + duration_td -%}
```

This relies on knowing that `module.datetime.timedelta` maps to Python's `datetime.timedelta`, understanding nanosecond-to-microsecond conversion, and trusting that datetime arithmetic works in Jinja2's evaluation context. It's not documented and fragile.

Note: Proposal #7 addresses timestamp *formatting* (ISO, syslog, Apache formats). This proposal addresses timestamp *arithmetic* — computing derived timestamps from the input timestamp, which is a different concern.

**Proposal**: Add offset/arithmetic methods directly on the `timestamp` object:

- `timestamp.add(milliseconds=N)` → new datetime offset by N ms
- `timestamp.add(seconds=N)` → new datetime offset by N seconds
- `timestamp.add(microseconds=N)` → new datetime offset by N μs
- `timestamp.subtract(seconds=N)` → new datetime offset backward

This would simplify the DNS example to:

```jinja2
{%- set duration_ns = module.rand.number.integer(1000000, 80000000) -%}
{%- set end_ts = timestamp.add(microseconds=duration_ns // 1000) -%}
```

Implementation: wrap the `datetime` timestamp in a thin proxy class that delegates all standard methods and adds `add()`/`subtract()` convenience methods.

---

## 17. Template API: No statistical distribution helpers beyond uniform and Gaussian

**Context**: Building the `network-firewall` generator (session durations, byte counts, packet counts).

**Problem**: Network firewall events need realistic session durations. Real firewall session durations follow a log-normal distribution — most sessions are short (DNS lookups: 5–50ms), some are moderate (web browsing: 1–30s), and a long tail is very long (streaming, VPN tunnels: minutes to hours). Using `module.rand.number.integer(100, 600000)` produces a flat uniform distribution where a 300-second session is as likely as a 1-second session, which looks nothing like real traffic.

The same problem applies to byte counts (should correlate with protocol and duration — DNS transfers kilobytes, video streaming transfers gigabytes) and inter-arrival times (bursty traffic follows exponential distributions, not uniform).

Currently `module.rand.number.gauss(mu, sigma)` is the only non-uniform distribution available, but:
- It can produce **negative values** for inherently positive quantities (session duration, byte count)
- It doesn't model the heavy right tails seen in real network data
- There's no log-normal, exponential, or Pareto distribution — the three most common in network traffic modeling

The workaround in the firewall generator was to use flat `integer(min, max)` ranges, which produces unrealistic-looking data that's immediately obvious in histograms and dashboards.

**Proposal**: Add common statistical distribution helpers to `module.rand.number`:

```
module.rand.number.lognormal(mu, sigma)     → always positive, right-skewed
module.rand.number.exponential(lambd)        → memoryless inter-arrival times
module.rand.number.pareto(alpha, xmin=1.0)   → heavy-tailed (file sizes, connection counts)
module.rand.number.triangular(low, high, mode) → peaked distribution with known bounds
```

All of these are one-liners wrapping Python's `random.lognormvariate()`, `random.expovariate()`, `random.paretovariate()`, and `random.triangular()` — zero external dependencies.

Additionally, add a clamping utility since distribution outputs often need bounding:
```
module.rand.number.clamp(value, min, max)   → bound any value to [min, max]
```

**Example — realistic session durations**:
```jinja
{# Log-normal: median ~2s, long tail up to minutes #}
{%- set duration_s = module.rand.number.lognormal(0.7, 1.5) -%}
{%- set duration_ms = module.rand.number.clamp(duration_s * 1000, 1, 3600000) | int -%}
```

**Example — realistic byte counts**:
```jinja
{# Pareto: most transfers small, some very large #}
{%- set bytes_raw = module.rand.number.pareto(1.5, 500) -%}
{%- set total_bytes = module.rand.number.clamp(bytes_raw, 64, 10000000) | int -%}
```

This would significantly improve the realism of any generator dealing with network metrics, system performance counters, or time-series data.

---

## 18. Samples: No `selectattr` with multiple conditions in a single filter

**Context**: Building `network-firewall` templates that filter hosts by both subnet and role.

**Problem**: Firewall templates frequently need to pick a random host matching multiple criteria — e.g., a server in the DMZ zone, or a workstation in the trust zone. Jinja2's `selectattr` only supports one condition at a time, requiring verbose chaining:

```jinja
{%- set srv = samples.internal_hosts
    | selectattr("role", "equalto", "server")
    | selectattr("subnet", "equalto", "servers")
    | list
    | random -%}
```

This is 4 filters for what is conceptually a single operation: "pick a random server from the servers subnet." Every template that needs filtered sampling repeats this pattern. In the firewall generator, this chain appears 6 times across different templates, each time for a different zone/role combination.

The chain is also fragile: if the filter produces an empty list, `| random` raises an error with no fallback mechanism. The template author must defensively check `| length > 0` before using `| random`, adding more boilerplate.

**Proposal**: Add a custom `| where` Jinja2 filter that accepts a dict of conditions:

```jinja
{%- set srv = samples.internal_hosts | where(role="server", subnet="servers") | random -%}
```

Or alternatively, add a `| random_where` that combines filtering and random selection with a built-in empty-list fallback:

```jinja
{%- set srv = samples.internal_hosts | random_where(role="server", subnet="servers", default=none) -%}
```

Implementation: register a custom Jinja2 filter via `env.filters['where']` that applies multiple `selectattr` conditions from keyword arguments. The `random_where` variant would additionally apply `| random` with a default for empty results.

---

## 19. Samples: No parameter interpolation in sample data files

**Context**: Building the `web-nginx` generator with referer patterns that include the configurable server hostname.

**Problem**: Sample data files (CSV, JSON) are loaded statically at plugin initialization and cannot reference `params.*`. In the nginx generator, referer strings naturally include the server's domain name (e.g., `https://example.com/products`). But because the domain is a configurable param (`params.server_name`), the workaround is storing literal placeholder strings in the CSV and manually replacing them in every template:

```csv
referer,type
https://${server_name}/,internal
https://${server_name}/products,internal
```

```jinja2
{%- set ref_entry = samples.referers | random -%}
{%- set referer = ref_entry.referer | replace("${server_name}", server_name) -%}
```

This is fragile (the `${server_name}` placeholder looks like Eventum's `${params.*}` substitution syntax but isn't — it's just a hand-rolled string convention), easy to forget, and must be repeated in every template that uses the sample. If a generator has 7 templates all using the same parameterized sample, you get 7 copies of the replacement logic.

The same issue applies to JSON sample files. For example, upstream URLs that include a configurable backend address, or file paths that include a configurable document root.

**Proposal**: Support `${params.*}` interpolation in sample data at load time. When `generator.yml` defines both `params` and `samples`, resolve `${params.*}` references in sample string values after loading:

```csv
referer,type
https://${params.server_name}/,internal
https://${params.server_name}/products,internal
```

The sample reader already has access to the params dict from the template config. Adding a recursive string replacement pass over loaded sample values would be a small change to `sample_reader.py` and would keep sample data DRY with the generator's configuration. Templates would then use sample values directly without manual replacement.

---

## 20. Samples: Pre-indexed grouping for O(1) filtered random access

**Context**: Building the `web-nginx` generator where URLs are categorized (page, asset, api, wellknown, probe) and user agents are typed (browser, mobile, bot, tool, monitor).

**Problem**: The nginx generator's access templates select URLs and user agents by category on every render. With 56 URLs and 24 user agents, this requires a full list scan to build a temporary filtered list each time:

```jinja2
{%- set category_urls = [] -%}
{%- for u in samples.urls if u.category == url_category -%}
  {%- do category_urls.append(u) -%}
{%- endfor -%}
{%- set url_entry = category_urls | random -%}
```

This 4-line pattern appears 4 times across the nginx access templates (filtering URLs by category, user agents by type). At 5 events/second, this means 20 full-list scans per second — O(n) per event for what should be a constant-time lookup.

Note: Proposal #18 addresses the ergonomics of filtering with a `| where` filter. This proposal addresses the **performance** concern — filtering at render time is wasteful when the categories are known at load time.

**Proposal**: Add an `index_by` option to sample definitions in `generator.yml` that pre-builds a grouped lookup dict at load time:

```yaml
samples:
  urls:
    type: json
    source: samples/urls.json
    index_by: category
  user_agents:
    type: csv
    source: samples/user_agents.csv
    header: true
    index_by: type
```

Then access in templates as:

```jinja2
{%- set url_entry = samples.urls.asset | random -%}
{%- set ua = samples.user_agents.browser | random -%}
```

At load time, the sample reader would group entries by the specified field and expose them as a dict of lists. This is O(1) lookup per render instead of O(n), self-documenting (the category names appear directly in template code), and requires zero boilerplate in templates.

Implementation: in `sample_reader.py`, after loading the data, if `index_by` is set, build a `defaultdict(list)` grouped by the field value. Expose the grouped dict through the same `samples.<name>` interface. Access to the ungrouped list (for backward compatibility) could remain available via `samples.<name>._all`.

---

## 21. Event plugin: Burst/fan-out mode for correlated multi-event groups

**Context**: Building the `web-nginx` generator where a single page load produces 10–30 correlated HTTP requests.

**Problem**: In real nginx traffic, a browser loading a page generates a burst of requests within a 1–3 second window: 1 HTML page + 2–4 CSS files + 3–6 JS bundles + 5–15 images + 1–3 font files + 1–2 API calls. All requests share the same source IP and have the HTML page URL as referer. This burst pattern is the fundamental unit of web traffic.

With the current `chance` mode, each event is independent — there's no way to say "when this template fires, also emit N related events with shared context." You can approximate it by weighting asset templates higher, but the events won't share source IPs or referers, making them uncorrelated noise rather than realistic page loads. Any dashboard showing "requests per user session" or "assets per page view" would show flat uniform distributions instead of the natural clustering.

Note: Proposal #6 addresses *sequential ordering* of different template types (A → B → C in a login flow). This proposal addresses *variable-count bursts* from a single template with shared per-burst context — a fundamentally different pattern. Sequences have a fixed step count and distinct templates per step; bursts have a variable count and reuse the same template with shared variables.

**Proposal**: Add a `burst` option to template entries in `chance` mode:

```yaml
templates:
  - page_load:
      template: templates/access-success.json.jinja
      chance: 300
      burst:
        count: [10, 30]     # random count between 10 and 30
        context:             # Jinja2 expressions evaluated once per burst
          burst_ip: "{{ module.rand.network.ip_v4_public() }}"
          burst_referer: "https://{{ params.server_name }}/"
```

When `page_load` is selected by the chance picker, the engine would:
1. Evaluate `context` expressions once, generating a single source IP, referer, etc.
2. Render the template `count` times (random between 10 and 30), passing the burst context as extra variables alongside the normal `params`, `samples`, `shared`
3. Emit all rendered events as a single batch

The template would use `burst.burst_ip` when available to produce correlated events, while still varying per-event fields (URL path, response size, user agent) normally:

```jinja2
{%- if burst is defined -%}
  {%- set src_ip = burst.burst_ip -%}
  {%- set referer = burst.burst_referer -%}
{%- else -%}
  {%- set src_ip = module.rand.network.ip_v4_public() -%}
  {%- set referer = "-" -%}
{%- endif -%}
```

This directly models the page-load burst pattern that dominates real web traffic, and would also be useful for other bursty data sources: SSH brute-force attempts (N login failures from same IP), log rotation events (burst of writes at rotation time), or monitoring scrapes (batch of metric queries from same collector).

---

## 22. Samples: JSON samples require homogeneous schemas (all objects must have identical keys)

**Context**: Building the `web-apache` generator with URL sample data where some entries have an `"extension"` field and others don't.

**Problem**: When loading JSON sample files, the sample reader creates a `tablib.Dataset` which requires all objects in the array to have the same set of keys. Real-world data often has optional fields — URL paths for static assets have a file extension while page/API URLs don't:

```json
[
    {"path": "/about", "type": "page", "min_bytes": 5000, "max_bytes": 15000},
    {"path": "/css/style.css", "extension": "css", "type": "static", "min_bytes": 5000, "max_bytes": 50000}
]
```

Loading this fails because the first entry is missing the `"extension"` key. The workaround is adding `"extension": null` to every entry without one — in web-apache this meant manually padding 27 out of 40 entries:

```json
{"path": "/about", "extension": null, "type": "page", "min_bytes": 5000, "max_bytes": 15000}
```

This is tedious, error-prone (forget one entry and loading breaks), and makes sample data files harder to read and maintain. Adding a new optional field to some entries requires editing every other entry to add the null placeholder.

**Proposal**: When loading JSON samples, compute the union of all keys across all objects and fill missing keys with `None` before creating the tablib Dataset:

```python
# In SamplesReader._load_json_sample():
all_keys: set[str] = set()
for obj in data:
    all_keys |= obj.keys()
for obj in data:
    for key in all_keys:
        obj.setdefault(key, None)
```

This matches how most data tools handle heterogeneous JSON (pandas `json_normalize`, DuckDB `read_json_auto`, jq). It's ~4 lines of code and eliminates a sharp edge that every JSON sample author will hit.

---

## 23. Template API: `module.rand.weighted_choice_by` for object sequences with weight attributes

**Context**: Building the `web-apache` generator where 4 of 5 access templates need "pick a random browser User-Agent (not a bot) weighted by market share."

**Problem**: The compound operation of filtering sample data by a field value, then doing a weighted random pick from the filtered subset, requires 8+ lines of boilerplate that was copy-pasted across 4 templates in web-apache:

```jinja
{%- set browser_uas = [] -%}
{%- set browser_weights = [] -%}
{%- for ua in samples.user_agents -%}
  {%- if ua.type == "browser" or ua.type == "tool" -%}
    {%- do browser_uas.append(ua) -%}
    {%- do browser_weights.append(ua.weight) -%}
  {%- endif -%}
{%- endfor -%}
{%- set ua = module.rand.weighted_choice(browser_uas, browser_weights) -%}
```

The core issue is that `module.rand.weighted_choice(items, weights)` requires two parallel lists. When the items are objects with a weight attribute, you must manually extract the parallel arrays — which forces the loop pattern. This is the #1 source of boilerplate in the web-apache generator.

Note: Proposal #8 proposes `| weighted_random` as a Jinja2 filter on samples. Proposal #18 proposes `| where` for filtering. Proposal #20 proposes `index_by` for pre-grouped access. This proposal addresses a different gap: telling `weighted_choice` to read weights from an attribute of the items themselves, eliminating the parallel-array extraction loop.

**Proposal**: Add `module.rand.weighted_choice_by(sequence, weight_attr)` — a variant that accepts a sequence of objects and a weight attribute name:

```python
def weighted_choice_by(self, items: Sequence, weight_attr: str) -> Any:
    weights = [getattr(item, weight_attr) for item in items]
    return self.weighted_choice(list(items), weights)
```

Combined with Jinja2's built-in `selectattr` (which already works with tablib Row objects), the 8-line pattern becomes 2 lines:

```jinja
{%- set browser_uas = samples.user_agents | selectattr('type', 'in', ['browser', 'tool']) | list -%}
{%- set ua = module.rand.weighted_choice_by(browser_uas, 'weight') -%}
```

If proposal #18's `| where` filter and #20's `index_by` were also implemented, it could become even cleaner:

```jinja
{%- set ua = module.rand.weighted_choice_by(samples.user_agents.browser, 'weight') -%}
```

---

## 24. Template API: Missing `module.rand.crypto.sha1()` hash generator

**Context**: Building the `windows-sysmon` generator (15 Sysmon event types with ECS-compatible output).

**Problem**: Sysmon events include file and process hashes in SHA1, MD5, SHA256, and IMPHASH formats. The `winlog.event_data.Hashes` field uses the compound format `SHA1=abc,MD5=def,SHA256=ghi,IMPHASH=jkl`, and ECS maps these into `process.hash.sha1`, `process.hash.md5`, `process.hash.sha256`, and `file.hash.*`.

The `module.rand.crypto` namespace currently provides `uuid4()`, `md5()`, and `sha256()` — but **no `sha1()`**. SHA1 is the default and most common hash format in Sysmon configurations, Windows Authenticode signatures, git commit hashes, and many other security data sources.

The workaround in the Sysmon generator was to use `module.rand.string.hex(40)` to produce a random 40-character hex string. This works but is semantically wrong — it bypasses the crypto namespace entirely and won't benefit from any future improvements (e.g., deterministic hashing from input).

```jinja2
{# Current workaround — wrong namespace, no semantic meaning #}
{%- set hash_sha1 = module.rand.string.hex(40) -%}
{%- set hash_md5 = module.rand.crypto.md5() -%}
{%- set hash_sha256 = module.rand.crypto.sha256() -%}
```

**Proposal**: Add `module.rand.crypto.sha1()` to match the existing `md5()` and `sha256()`:

```jinja2
{%- set hash_sha1 = module.rand.crypto.sha1() -%}
```

Implementation: one-liner in `rand.py`'s `CryptoRandom` class, identical pattern to the existing `md5()` and `sha256()` methods — generate 20 random bytes and hex-encode.

Additionally, consider adding `module.rand.crypto.imphash()` as an alias for `md5()` (since PE import hashes are MD5-based) for semantic clarity in Windows security generators.

---

## 25. Template API: No path manipulation filters for file path decomposition

**Context**: Building Windows Sysmon templates where ECS requires separate `file.name`, `file.directory`, and `file.extension` fields derived from a single `file.path`.

**Problem**: The Sysmon generator has 5 templates that work with file paths (Events 11, 15, 23, 26, plus Event 1 for process paths). Each template must decompose a full Windows path into its component parts for ECS compliance. This requires the same 3 lines of boilerplate in every file-related template:

```jinja2
{%- set path_parts = target_filename.split("\\") -%}
{%- set file_name = path_parts[-1] -%}
{%- set file_directory = "\\".join(path_parts[:-1]) -%}
```

For templates that also need the file extension, a 4th line is added:

```jinja2
{%- set file_ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "" -%}
```

This pattern is repeated verbatim across 5 templates in the Sysmon generator and is error-prone — the backslash separator must be doubled (`"\\"`) in Jinja2 strings, and using `[:-1]` vs `[-1]` incorrectly produces wrong results silently. The same problem affects Linux path decomposition (using `/`) in the auditd generator's file operation templates.

**Proposal**: Add path manipulation Jinja2 filters that handle both Unix and Windows separators:

```jinja2
{%- set file_name = target_filename | basename -%}
{# → "svchost.exe" from "C:\Windows\System32\svchost.exe" #}

{%- set file_dir = target_filename | dirname -%}
{# → "C:\Windows\System32" #}

{%- set file_ext = target_filename | fileext -%}
{# → "exe" (without leading dot) #}
```

Implementation: register 3 custom Jinja2 filters that handle both `/` and `\` separators:

```python
def basename_filter(path: str) -> str:
    sep_idx = max(path.rfind('/'), path.rfind('\\'))
    return path[sep_idx + 1:] if sep_idx >= 0 else path

def dirname_filter(path: str) -> str:
    sep_idx = max(path.rfind('/'), path.rfind('\\'))
    return path[:sep_idx] if sep_idx >= 0 else ''

def fileext_filter(path: str) -> str:
    name = basename_filter(path)
    dot_idx = name.rfind('.')
    return name[dot_idx + 1:] if dot_idx >= 0 else ''
```

These 3 filters would eliminate ~15 lines of duplicated path manipulation across the Sysmon generator alone, and benefit every generator that produces file system events (auditd, sysmon, nginx, apache).

---

## 26. Samples: No render-time variable interpolation in sample data values

**Context**: Building Sysmon templates with file and registry paths that contain dynamic segments.

**Problem**: Sample data files often contain paths with placeholders that must be resolved using *template-scoped variables* (not params — those are covered by proposal #19). In the Sysmon generator, `file_paths.json` and `registry_paths.json` use placeholders like `{USER}`, `{GUID}`, and `{SID}`:

```json
{"path": "C:\\Users\\{USER}\\AppData\\Local\\Temp\\{GUID}.tmp", "extension": "tmp"},
{"path": "HKU\\{SID}\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU"}
```

Every template that uses these samples must manually chain `| replace()` calls to resolve the placeholders from template-local variables:

```jinja2
{%- set target = fp.path
    | replace("{USER}", user_name)
    | replace("{GUID}", module.rand.crypto.uuid4())
    | replace("{SID}", domain_sid ~ "-" ~ module.rand.number.integer(1000, 9999))
-%}
```

This 4-line replacement chain appears in 7 templates across the Sysmon generator (Events 11, 12, 13, 15, 23, 26 for file paths, and 12/13 for registry paths). Each template must know the complete set of placeholders and their resolution logic. If a new placeholder is added to the sample data, every consuming template must be updated.

Note: Proposal #19 addresses `${params.*}` interpolation at *load time* — resolving config-level parameters when samples are first read. This proposal addresses a different layer: resolving *template-scoped variables* (usernames, GUIDs, SIDs) that only exist at *render time* and change with every event.

**Proposal**: Add a `| interpolate(vars)` Jinja2 filter that resolves `{key}` placeholders from a dict:

```jinja2
{%- set vars = {
    "USER": user_name,
    "GUID": module.rand.crypto.uuid4(),
    "SID": domain_sid ~ "-" ~ module.rand.number.integer(1000, 9999)
} -%}
{%- set target = fp.path | interpolate(vars) -%}
```

Implementation:

```python
def interpolate_filter(value: str, mapping: dict) -> str:
    for key, replacement in mapping.items():
        value = value.replace(f"{{{key}}}", str(replacement))
    return value

env.filters['interpolate'] = interpolate_filter
```

This collapses the 4-line replacement chain into 2 lines (define mapping + apply filter) and centralizes the placeholder→variable mapping in one place per template rather than scattering it across multiple `| replace()` calls.

---

## 27. Config: No early validation of `${params.*}` / `${secrets.*}` references

**Context**: Investigating the v2.0.2 bug where the API returned validation errors for configs with placeholders, and reviewing the config loading pipeline in `config_loader.py`.

**Problem**: When a generator config uses `${params.opensearch_host}` or `${secrets.api_key}`, there is no validation at startup that the referenced params and secrets actually exist. The substitution in `config_loader.py` only runs when the generator starts executing — which can be minutes after app startup. If a param is missing, the generator crashes with a `ValueError` at runtime. In multi-generator setups, one generator may start fine while another fails later due to a typo in a param name.

**Example**: A config references `${params.opensearch_host}` but `startup.yml` only defines `opensearch_url`. The app starts successfully, the generator begins processing, then crashes on first config load. The error message shows the missing key but offers no suggestion for the closest match.

**Proposal**: Add startup-time validation that cross-references all `${params.*}` and `${secrets.*}` tokens found in generator configs against the params defined in `startup.yml` and the secrets available in the keyring. Warn (or fail-fast with a `--strict` flag) if any references are unresolvable. Consider including "did you mean?" suggestions using edit distance for near-matches.

---

## 28. Output: No retry or dead-letter mechanism for failed writes

**Context**: Reviewing the executor's output error handling in `executor.py` — `PluginWriteError` is logged and the batch is discarded with no recovery path.

**Problem**: When an output plugin fails to deliver events (e.g., OpenSearch is temporarily unreachable, HTTP endpoint returns 500), the failed events are silently discarded. The executor logs the error and moves on to the next batch. There is no retry logic, no dead-letter queue, and no way to recover lost events. The only indicator is a `write_failed` counter in stats — but the actual event data is gone.

**Example**: A generator writes to OpenSearch at 1000 EPS. OpenSearch goes down for 30 seconds during a network blip. All events in that window are permanently lost. The operator sees `write_failed` increase in stats but cannot replay the lost events. For continuous monitoring scenarios, this creates gaps that trigger false-positive alerts downstream.

**Proposal**: Add configurable retry behavior to output plugins:
```yaml
output:
  - opensearch:
      hosts: ["${params.opensearch_host}"]
      retry:
        max_attempts: 3
        backoff: exponential    # linear | exponential | fixed
        initial_delay: 1.0      # seconds
      dead_letter:
        path: ./dead_letter/    # write failed events to files for later replay
```
The dead-letter directory would store failed events as timestamped JSON files that can be replayed with the `replay` event plugin, creating a natural recovery loop within Eventum's own pipeline.

---

## 29. Generator: No lifecycle event hooks

**Context**: Reviewing `InstanceHooks` in `hooks.py` — only app-level `terminate`, `restart`, and `get_settings_file_path` exist. No per-generator hooks for start, stop, or error events.

**Problem**: There is no way to hook into individual generator lifecycle events. This makes it impossible to implement common operational patterns like sending a notification when a generator crashes, running cleanup logic on shutdown, or exporting custom metrics on completion.

**Example**: In a production deployment with 10 generators, one crashes due to an OpenSearch connection timeout. The operator has no way to get notified except by polling the `/generators` API endpoint or watching logs. There's no webhook, callback, or event system to react to generator state changes programmatically.

**Proposal**: Add generator-level lifecycle hooks configurable in `eventum.yml` or per-generator config:
```yaml
hooks:
  on_start: "curl -s -X POST ${params.webhook_url} -d '{\"event\": \"started\", \"id\": \"${id}\"}'"
  on_error: "curl -s -X POST ${params.webhook_url} -d '{\"event\": \"error\", \"id\": \"${id}\"}'"
  on_stop: "curl -s -X POST ${params.webhook_url} -d '{\"event\": \"stopped\", \"id\": \"${id}\"}'"
```
Or a Python callback interface registered via API for programmatic integrations.

---

## 30. Config: No hot-reload for running generators

**Context**: Understanding the generator restart flow — updating a config requires stopping and restarting the generator via `GeneratorManager`, or SIGHUP to restart the entire app.

**Problem**: Updating a generator's config (changing a template, adding a new event type, adjusting chance weights) requires stopping the generator and restarting it. The only alternative is a full app restart via SIGHUP, which stops *all* generators. For long-running generators producing continuous event streams, this creates gaps in the output.

**Example**: A generator is producing events at 1000 EPS to OpenSearch. The operator wants to add a new event type template. They must stop the generator (creating a gap in the event stream), update the config file, and restart. In 24/7 monitoring scenarios, any gap triggers false-positive alerts downstream.

**Proposal**: Add a config reload API endpoint (`POST /generators/{id}/reload`) that:
1. Loads and validates the new config from disk
2. Gracefully drains the current pipeline (finishes in-flight batches)
3. Re-initializes plugins with the new config
4. Resumes generation without losing events

For the CLI, support `SIGUSR1` per-generator or an `eventum reload --id <generator>` command.

---

## 31. CLI: Config inspection command for discoverability

**Context**: Setting up generators and needing to reverse-engineer which `${params.*}` and `${secrets.*}` a config expects by reading YAML and template files manually. Related to proposal #27 (early validation) — inspection is the user-facing complement.

**Problem**: There is no way to inspect what a generator config expects without reading the YAML and all referenced template files manually. When setting up a new deployment, the operator must find every `${params.*}` and `${secrets.*}` token across the config and templates, then create matching entries in `startup.yml` and the keyring. Template params (referenced via `{{ params.domain }}` inside `.json.jinja` files) are especially hard to discover since they're scattered across many files.

**Example**: Setting up `windows-security` which uses `${params.opensearch_host}`, `${params.opensearch_user}`, `${params.opensearch_index}`, and `${secrets.opensearch_password}` in the output section, plus `hostname`, `domain`, and other params referenced inside 11 template files. Missing any one causes a runtime crash.

**Proposal**: Add an `eventum inspect --path <generator.yml>` command that outputs:
```
Generator: windows-security

Required params (generator.yml):
  - opensearch_host     (output.opensearch.hosts)
  - opensearch_user     (output.opensearch.http_auth)
  - opensearch_index    (output.opensearch.index)

Required secrets (generator.yml):
  - opensearch_password (output.opensearch.http_auth)

Template params (via {{ params.* }}):
  - hostname            (templates/4624-logon-success.json.jinja, +10 more)
  - domain              (templates/4624-logon-success.json.jinja, +8 more)
```
This would make generator setup self-documenting and could be combined with proposal #27 to catch mismatches before runtime.

---

## 32. Bug: Stdout output plugin crashes with `writelines` — `NonFileStreamWriter` incompatibility

**Context**: Building and validating the `network-checkpoint` generator (Check Point Security Gateway, 11 templates, 8 software blades).

**Problem**: The stdout output plugin crashes immediately on first write with:

```
AttributeError: 'NonFileStreamWriter' object has no attribute 'writelines'
```

The plugin's `_write()` method at `eventum/plugins/output/plugins/stdout/plugin.py:75` calls `self._writer.writelines(lines)`, but `self._writer` is a `NonFileStreamWriter` from the `aioconsole` library (returned by `get_standard_streams()`), which only implements `write()` and `drain()` — not `writelines()`.

This means **stdout output is completely broken** for any generator. The entire network-checkpoint validation had to be done by switching to the `file` output plugin:

```yaml
# Cannot use:
output:
  - stdout:
      formatter:
        format: json

# Workaround:
output:
  - file:
      path: /tmp/test-output.jsonl
      formatter:
        format: json
```

**Fix**: Replace `self._writer.writelines(lines)` with a loop:

```python
for line in lines:
    self._writer.write(line)
```

Or concatenate into a single write: `self._writer.write(b''.join(lines))`.

This is a one-line fix that unblocks the most common testing workflow.

---

## 33. Samples: Rows are plain tuples — no named field access despite headers/keys

**Context**: Building the `network-checkpoint` generator with 8 sample data files (CSV with headers, JSON with object keys).

**Problem**: Sample data loaded via `tablib.Dataset` returns rows as **plain Python tuples**, not dicts or named tuples. This means field names from CSV headers and JSON object keys are completely inaccessible at render time. All field access must use positional indices.

This was the single most time-consuming bug during network-checkpoint development — all 11 templates were initially written with named attribute access (the natural expectation), and every one had to be rewritten with positional indices after discovering that `tablib.Dataset[i]` returns `tuple`.

**Expected** (how every template was first written):

```jinja2
{%- set host = samples.internal_hosts | random -%}
{%- set src_ip = host.ip -%}
{%- set hostname = host.hostname -%}
{%- set subnet = host.subnet -%}
```

**Actual** (what works — positional index only):

```jinja2
{#- internal_hosts.csv: 0=ip, 1=hostname, 2=mac, 3=subnet, 4=role -#}
{%- set host = samples.internal_hosts | random -%}
{%- set src_ip = host[0] -%}
{%- set hostname = host[1] -%}
{%- set subnet = host[3] -%}
```

The consequences are severe:

1. **Every template needs column-index comments** — Each template must document the column layout as a comment (`0=ip, 1=hostname, 2=mac, ...`) so future editors can understand what `host[3]` means. In network-checkpoint, this is 8 different index maps across 11 templates.

2. **Jinja2's `selectattr` filter is unusable** — `selectattr("subnet", "equalto", "dmz")` fails because tuples have no named attributes. The workaround is a verbose manual loop:

   ```jinja2
   {%- set dmz_hosts = [] -%}
   {%- for h in samples.internal_hosts if h[3] == "dmz" -%}
     {%- do dmz_hosts.append(h) -%}
   {%- endfor -%}
   ```

3. **Fragile to schema changes** — Adding a column to a CSV shifts all subsequent indices. If `internal_hosts.csv` gains a new `os` column at position 2, every template using `host[2]` (mac), `host[3]` (subnet), `host[4]` (role) must be updated.

4. **Multiple existing proposals assume named access works** — Proposals #5 (flat dict), #18 (`selectattr` with multiple conditions), #20 (pre-indexed grouping), and #23 (`weighted_choice_by` with attribute name) all assume rows support `row.fieldname`. None of them can be implemented until this fundamental issue is fixed.

**Proposal**: Change `sample_reader.py` to return rows with named field access. Options:

**Option A** — Use `tablib.Dataset.dict` to iterate as dicts:

```python
class Sample:
    def __getitem__(self, key):
        row = self._dataset[key]
        if self._dataset.headers:
            return dict(zip(self._dataset.headers, row))
        return row
```

**Option B** — Wrap rows in `namedtuple` (preserves both index and named access):

```python
from collections import namedtuple

class Sample:
    def __init__(self, dataset):
        self._dataset = dataset
        if dataset.headers:
            self._RowType = namedtuple('Row', dataset.headers)
        else:
            self._RowType = None

    def __getitem__(self, key):
        row = self._dataset[key]
        if self._RowType:
            return self._RowType(*row)
        return row
```

Option B is preferred because it preserves backward compatibility (index access `row[0]` still works) while adding named access (`row.ip`). It also makes `selectattr` and `| weighted_random` proposals viable.

---

## 34. Config: `${params.*}` tokens extracted from YAML comments cause false-positive missing-params errors

**Context**: Building the `network-checkpoint` generator with a commented-out OpenSearch output section.

**Problem**: The config loader's token extraction (`config_loader.py:20`) uses a regex `r'\${\s*?(\S*?)\s*?}'` that scans the **entire raw YAML file content**, including comments. Any `${params.*}` token inside a YAML comment is treated as a required parameter, causing a startup failure when the param isn't provided.

This is the natural pattern — you want to include a ready-to-use OpenSearch config block in comments so users can uncomment it:

```yaml
output:
  - stdout:
      formatter:
        format: json

  # Production output — uncomment and configure:
  # - opensearch:
  #     hosts:
  #       - ${params.opensearch_host}
  #     username: ${params.opensearch_user}
  #     password: ${secrets.opensearch_password}
  #     index: ${params.opensearch_index}
```

This fails at startup with:

```
Parameters {'opensearch_host', 'opensearch_index', 'opensearch_user'} are missing
```

The workaround is to remove all `${...}` syntax from comments and replace with plain example values:

```yaml
  # - opensearch:
  #     hosts:
  #       - https://localhost:9200
  #     username: admin
  #     index: logs-checkpoint.firewall-default
```

This defeats the purpose of the commented template — users can't simply uncomment it and provide params; they have to rewrite the values.

**Proposal**: Strip YAML comments before token extraction. Add a preprocessing step in `config_loader.py`:

```python
def _strip_yaml_comments(content: str) -> str:
    """Remove YAML comments before token extraction."""
    lines = []
    for line in content.splitlines():
        # Find the first # that's not inside a quoted string
        stripped = line.lstrip()
        if stripped.startswith('#'):
            lines.append('')  # full-line comment → empty
        else:
            lines.append(line)
    return '\n'.join(lines)
```

Then in `load_config()`:

```python
content = file_path.read_text()
content_without_comments = _strip_yaml_comments(content)
extracted_params = extract_params(content_without_comments)
# ... but still substitute in the original content for YAML parsing
```

This preserves the current substitution behavior for active config values while ignoring tokens in comments. A more robust implementation could use a proper YAML-aware comment stripper, but even the simple line-level approach covers the primary use case (full-line `# - opensearch:` comment blocks).

---

## 35. Samples: JSON sample loading silently coerces numeric types to match first-row schema

**Context**: Building the `network-checkpoint` generator with JSON samples containing mixed numeric types.

**Problem**: When `tablib` loads a JSON array into a `Dataset`, it infers column types from the data. If a JSON field is an integer in some rows and absent/null in others, the type handling is inconsistent. More critically, because rows are returned as tuples (see proposal #33), there's no way to verify at load time that a field the template expects as an integer is actually loaded as one.

In the network-checkpoint generator, `ips_signatures.json` has a `severity_num` field that's an integer (1–4) used directly in JSON output:

```json
[["asm_dynamic_prop_SQL_FINGERPRINT_A", "SQL Injection via HTTP Request", "IPS", "SQL Injection", "...", "High", 3, "4", "2", "CVE-2024-23897", "http", 15]]
```

When accessed as `sig[6]`, the template outputs `"severity": 3` (integer). But if `tablib` coerces it to a string during loading, the output becomes `"severity": "3"` — invalid for ECS which expects a numeric type. This type mismatch is invisible until you validate the JSON output against an ECS schema.

**Proposal**: Add type-preservation guarantees to JSON sample loading:

1. When loading JSON samples, preserve the original JSON types (int, float, string, bool, null) rather than letting tablib normalize them
2. Optionally, support a `schema` field in sample config that declares expected column types:

```yaml
samples:
  ips_signatures:
    type: json
    source: samples/ips_signatures.json
    schema:
      severity_num: int
      weight: int
      confidence_level: str
```

This would catch type mismatches at load time (generator startup) rather than at render time (first event), and would provide clear error messages like `"Sample 'ips_signatures' column 'severity_num': expected int, got str at row 3"`.

---

## 36. Template API: No `| tojson_value` filter for conditional JSON field emission

**Context**: Building 11 Check Point templates where many JSON fields are conditionally included based on event type.

**Problem**: When a JSON field should only appear under certain conditions, managing trailing commas around `{% if %}` blocks is error-prone. The existing `| tojson` filter serializes a Python value as JSON, but there's no filter that emits a complete `"key": value` pair conditionally with proper comma handling.

In the network-checkpoint generator, the IPS templates conditionally include `industry_reference` (CVE ID) and the VPN template conditionally includes `ike` and `ike_ids` fields:

```jinja2
    "version": "5"{% if sig[9] %},
    "industry_reference": "{{ sig[9] }}"{% endif %}
```

The comma must go **before** the conditional field when it's the last field, but **after** the preceding field when it's a middle field. Getting this wrong produces invalid JSON that only fails at runtime. Across 11 templates with 3–5 conditional fields each, this is ~40 comma-placement decisions.

Note: Proposal #15 proposes a `format: json` post-processing mode that strips trailing commas. This proposal addresses a different layer — providing a template-level tool to avoid generating the bad commas in the first place, which is useful even without post-processing.

**Proposal**: Add a `| json_field(key)` Jinja2 filter that emits a properly formatted JSON key-value pair (or nothing if the value is None/empty), designed to be used in comma-safe patterns:

```jinja2
{# Emit key-value pair only if value is truthy, with leading comma #}
{{ sig[9] | json_field("industry_reference", comma="before") }}
```

Would output either `, "industry_reference": "CVE-2024-23897"` or empty string.

Alternatively, a simpler approach: add a `| strip_trailing_commas` filter that can be applied to the entire template output:

```jinja2
{{ output | strip_trailing_commas }}
```

Implementation: register a filter that removes commas before `}` or `]` in JSON strings — a ~5-line regex.

---

## 37. Template API: `module.rand.string.hex()` inconsistent bit width — no fixed-byte hex generator

**Context**: Building Check Point `loguid` fields that require exact hex segment lengths.

**Problem**: `module.rand.string.hex(n)` generates `n` random hex characters (nibbles), not `n` bytes. This is confusing when the goal is to produce values that match a specific byte width. Check Point's `loguid` format is `{0x<ts_hex>,0x<1byte>,0x<4bytes>,0xc<3.5bytes>}`, which maps to `hex(8), hex(1), hex(8), hex(7)` character counts — not byte counts.

The current API is:

```jinja2
{%- set loguid = "{0x%s,0x%s,0x%s,0x%s}" | format(
    ts_hex,
    module.rand.string.hex(1),    ← 1 hex char = 0.5 bytes (unusual)
    module.rand.string.hex(8),    ← 8 hex chars = 4 bytes
    "c" ~ module.rand.string.hex(7)  ← 7 hex chars = 3.5 bytes
) -%}
```

Using `hex(1)` to produce a single hex nibble is counterintuitive. In most hex-generation contexts (UUIDs, hashes, tokens), you think in bytes. A `hex_bytes(n)` function that produces `2*n` hex characters (representing `n` random bytes) would be more natural for most use cases.

**Proposal**: Add `module.rand.string.hex_bytes(n)` that generates `n` random bytes as `2*n` hex characters:

```python
def hex_bytes(self, count: int) -> str:
    return secrets.token_hex(count)  # n bytes → 2n hex chars
```

This provides a byte-oriented API alongside the existing nibble-oriented `hex()`. The existing `hex(n)` would remain unchanged for backward compatibility. For the common case of generating hash-like values (MD5 = 16 bytes, SHA1 = 20 bytes, SHA256 = 32 bytes), `hex_bytes` is more natural than counting hex character widths.
