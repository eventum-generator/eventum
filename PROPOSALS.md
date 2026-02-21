# Eventum Improvement Proposals

Feedback gathered from building content-pack generators (linux-auditd, windows-security, etc.) using the template engine and generator.yml pipeline.

---

# 🐛 Bugs

## 48. Bug: `module.rand.network.ip_v4_public()` should exclude bogon/reserved ranges `[Medium]`

**Context**: Building the `network-fortigate` generator where source IPs for inbound traffic must be public and non-reserved.

**Problem**: `module.rand.network.ip_v4_public()` generates random public IPv4 addresses, but the generated addresses occasionally fall into reserved ranges that wouldn't appear in real internet traffic — documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24), benchmarking (198.18.0.0/15), CGNAT (100.64.0.0/10), or multicast (224.0.0.0/4). While these are technically not RFC 1918 private, they're not routable on the public internet and would never appear as source IPs in FortiGate traffic logs.

The FortiGate generator uses `ip_v4_public()` extensively in `traffic-forward-deny` (attack sources), `utm-ips` (intrusion sources), `utm-anomaly` (DoS sources), and `event-vpn` (remote tunnel endpoints). Over thousands of events, a small percentage will have documentation-range source IPs, which looks unrealistic in dashboards and can confuse SOC analysts testing detection rules.

**Proposal**: Ensure `module.rand.network.ip_v4_public()` excludes all IANA special-purpose address ranges (not just RFC 1918), or add an `ip_v4_routable()` variant that only produces genuinely routable addresses:

Excluded ranges should include (per IANA IPv4 Special-Purpose Address Registry):

- 0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16
- 172.16.0.0/12, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24
- 192.168.0.0/16, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24
- 224.0.0.0/3 (multicast + reserved)

---

## 22. Bug: JSON samples require homogeneous schemas (all objects must have identical keys) `[Medium]`

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

## 24. Bug: Missing `module.rand.crypto.sha1()` hash generator (API inconsistency) `[Low]`

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

# ✨ Features

## Template API

### 43. Template API: `module.rand.weighted_choice()` should accept a dict directly `[High]`

**Context**: Building 13 Suricata templates that use weighted random selection for status codes, response codes, and protocol choices.

**Problem**: `module.rand.weighted_choice(items, weights)` requires two parallel lists, but the most natural way to express item→weight mappings in Jinja2 is a dict. Every weighted choice in the Suricata generator required an awkward dict-to-parallel-lists conversion:

```jinja2
{%- set rcode_weights = {"NOERROR": 90, "NXDOMAIN": 8, "SERVFAIL": 2} -%}
{%- set rcode = module.rand.weighted_choice(rcode_weights | list, rcode_weights.values() | list) -%}
```

This pattern appears 15+ times across the 13 Suricata templates — for DNS rcodes, HTTP status codes, HTTP methods, TCP flow states, anomaly types, DHCP message types, alert actions, and direction choices. Each instance requires the same `| list` and `| values() | list` extraction.

**Proposal**: Make `weighted_choice` accept a dict where keys are items and values are weights:

```python
def weighted_choice(self, items_or_dict, weights=None):
    if isinstance(items_or_dict, dict):
        items = list(items_or_dict.keys())
        weights = list(items_or_dict.values())
    else:
        items = items_or_dict
    return random.choices(items, weights=weights, k=1)[0]
```

Template code becomes:

```jinja2
{%- set rcode = module.rand.weighted_choice({"NOERROR": 90, "NXDOMAIN": 8, "SERVFAIL": 2}) -%}
```

One line instead of two, and the intent is immediately clear. Backward-compatible since the existing two-argument call still works.

---

### 17. Template API: No statistical distribution helpers beyond uniform and Gaussian `[High]`

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

### 40. Template API: No `selectattr` "in" test for membership filtering `[High]`

**Context**: Building Snort templates where internal hosts have different roles (workstation, server, dmz) and templates need hosts matching specific role sets.

**Problem**: Jinja2's `selectattr` filter supports tests like `"equalto"`, `"ne"`, `"gt"`, `"lt"` — but not `"in"` for membership testing. When a template needs to select items matching one of several values, `selectattr` can't express this in a single filter:

```jinja2
{#- This does NOT work — "in" is not a valid selectattr test -#}
{%- set servers = samples.internal_hosts | selectattr("role", "in", ["server", "dmz"]) | list -%}

{#- Workaround: chain multiple equalto filters and merge, or use a manual loop -#}
{%- set servers = [] -%}
{%- for h in samples.internal_hosts -%}
  {%- if h.role in ["server", "dmz"] -%}
    {%- do servers.append(h) -%}
  {%- endif -%}
{%- endfor -%}
```

In the Snort generator, this forced replacing filtered sampling with simpler `| random` on the entire host list, losing the ability to restrict certain event types to specific host roles (e.g., web attacks should only target servers/DMZ, not workstations).

Note: This is a Jinja2 limitation, not an Eventum-specific bug. However, Eventum's template engine registers custom filters/tests (e.g., the `do` extension), so it can register additional tests.

**Proposal**: Register a custom `"in"` test for `selectattr`:

```python
def in_test(value, seq):
    return value in seq

env.tests['in'] = in_test
```

This would enable the natural pattern:

```jinja2
{%- set servers = samples.internal_hosts | selectattr("role", "in", ["server", "dmz"]) | list -%}
```

One line of Python, major ergonomic improvement for any generator that filters sample data by category.

---

### 25. Template API: No path manipulation filters for file path decomposition `[Medium]`

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

### 13. Template API: Missing `module.rand.network.ip_v4_in_subnet(cidr)` for targeted IP generation `[Medium]`

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

### 7. Template API: No `timestamp` formatting helpers `[Medium]`

**Problem**: The `timestamp.isoformat()` method works for `@timestamp`, but auditd's raw `msg=audit(epoch:serial)` format requires `timestamp.timestamp()`. Other formats (syslog's `MMM dd HH:MM:SS`, Apache's `[dd/Mon/yyyy:HH:mm:ss +0000]`) need `strftime()`. Each generator reinvents timestamp formatting.

**Proposal**: Add built-in timestamp format helpers or document common patterns:
- `timestamp.epoch()` → Unix epoch (float)
- `timestamp.syslog()` → `Feb 21 12:00:01` format
- `timestamp.apache()` → `[21/Feb/2026:12:00:01 +0000]` format

---

### 16. Template API: Timestamp arithmetic helper `[Medium]`

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

### 12. Template API: Missing `module.rand.network.ip_v6()` generator `[Medium]`

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

### 41. Template API: No duration formatting helper for human-readable time strings `[Medium]`

**Context**: Building the `vpn-cisco-anyconnect` generator where session disconnect events (ASA message 113019) include session duration in `Xh:Ym:Zs` format (e.g., `7h:32m:15s`).

**Problem**: Converting a duration in seconds to a human-readable string requires 4 lines of manual integer arithmetic in every template that deals with durations:

```jinja2
{%- set dur_hours = duration_secs // 3600 -%}
{%- set dur_minutes = (duration_secs % 3600) // 60 -%}
{%- set dur_seconds = duration_secs % 60 -%}
{%- set duration_str = "%dh:%02dm:%02ds" | format(dur_hours, dur_minutes, dur_seconds) -%}
```

This pattern is needed whenever log formats include human-readable durations: Cisco ASA session disconnect (`7h:32m:15s`), firewall session end (`duration=300`), DHCP lease time (`1d:0h:0m`), HTTP request time (`0.045s`). Each format is slightly different but the decomposition logic (seconds → hours/minutes/seconds or days/hours/minutes) is identical.

The Cisco ASA syslog format specifically uses `Duration: Xh:Ym:Zs` in message 113019. Other vendors use different formats: Palo Alto uses `elapsed=Xs`, FortiGate uses `duration=X`, Check Point uses `session_duration: X`. All require the same base conversion from total seconds.

**Proposal**: Add a `| format_duration` filter (or `module.time.format_duration()` function) with configurable format patterns:

```jinja2
{#- Cisco ASA format -#}
{%- set duration_str = duration_secs | format_duration('%Hh:%Mm:%Ss') -%}
{#- → "7h:32m:15s" -#}

{#- Simple HH:MM:SS -#}
{%- set duration_str = duration_secs | format_duration('%H:%M:%S') -%}
{#- → "07:32:15" -#}

{#- ISO 8601 duration -#}
{%- set duration_str = duration_secs | format_duration('iso8601') -%}
{#- → "PT7H32M15S" -#}

{#- With days for long durations -#}
{%- set duration_str = duration_secs | format_duration('%dd:%Hh:%Mm') -%}
{#- → "0d:7h:32m" -#}
```

The filter would accept total seconds (int or float) and a format string with `%D` (days), `%H` (hours), `%M` (minutes), `%S` (seconds), `%f` (fractional seconds). Predefined aliases like `'iso8601'` and `'hms'` would cover common cases. This eliminates the manual arithmetic and makes the intent self-documenting.

---

### 49. IANA protocol number ↔ transport name mapping helper `[Medium]`

**Context**: Building the `network-juniper-srx` generator where the Elastic integration expects both `network.iana_number` (string) and `network.transport` (name) in every event.

**Problem**: Every network security generator needs to produce both the IANA protocol number (e.g., `"6"`) and the transport name (e.g., `"tcp"`) because ECS uses both fields. The Elastic Juniper SRX integration maps `protocol-id` to `network.iana_number` and derives `network.transport` via a lookup table (0=hopopt, 1=icmp, 6=tcp, 17=udp, 47=gre, 50=esp, etc.).

In the Juniper SRX generator, this forced storing both values redundantly in `network_services.json`:

```json
{"port": 443, "protocol_id": "6", "transport": "tcp", "name": "junos-https", "weight": 40}
```

Every network generator (firewall, checkpoint, cisco, snort, suricata, dns, fortigate, juniper-srx) independently maintains this same mapping — some inline in templates, some in sample data, some hardcoded in weighted choice lists. The IDP template needed an `attack_services` dict with both protocol_id and transport for each service. The screen-alert template hardcoded protocol metadata per screen type.

Across all 12 network generators in content-packs, the iana↔transport mapping appears in ~35 locations.

**Proposal**: Add bidirectional IANA protocol mapping helpers to `module.rand.network`:

```python
module.rand.network.iana_to_transport(6)        # → "tcp"
module.rand.network.iana_to_transport("17")     # → "udp" (accepts string too)
module.rand.network.transport_to_iana("tcp")    # → "6" (returns string for ECS)
module.rand.network.transport_to_iana("icmp")   # → "1"
```

Implementation: a ~15-entry static dict covering the protocols that appear in real firewall/IDS logs (tcp, udp, icmp, gre, esp, ipv6-icmp, sctp, igmp, vrrp, hopopt). One dict, two lookup functions, ~20 lines of code.

This would allow sample data to store only the port and protocol number (or name), with the template deriving the other:

```jinja2
{%- set transport = module.rand.network.iana_to_transport(service.protocol_id) -%}
```

---

### 1. Template API: Missing `module.rand.network.ip_v4_private()` (any range) `[Low]`

**Problem**: When generating network events, you often need "some private IP" regardless of class. Currently you must pick between `ip_v4_private_a()`, `ip_v4_private_b()`, or `ip_v4_private_c()` — which forces the generator author to hardcode a subnet class or add a weighted choice between three functions.

**Proposal**: Add a generic `module.rand.network.ip_v4_private()` that randomly picks from any RFC 1918 range with realistic weights (most traffic is /24 class C).

---

### 2. Template API: No `module.rand.network.port()` helpers `[Low]`

**Problem**: Generating realistic port numbers requires manual `module.rand.number.integer(49152, 65535)` for ephemeral ports or hardcoded weighted choices for well-known ports. Every generator repeats this logic.

**Proposal**: Add convenience helpers:
- `module.rand.network.ephemeral_port()` → random port in 49152–65535
- `module.rand.network.well_known_port()` → weighted random from common ports (80, 443, 22, 53, etc.)

---

### 14. Template API: Missing `module.rand.network.community_id()` for Elastic network events `[Low]`

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

### 23. Template API: `module.rand.weighted_choice_by` for object sequences with weight attributes `[Low]`

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

### 37. Template API: `module.rand.string.hex()` inconsistent bit width — no fixed-byte hex generator `[Low]`

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

---

### 45. `module.rand.geo` helpers for realistic geographic data generation `[Low]`

**Context**: Building the `network-fortigate` generator where traffic events need source/destination country codes and names for GeoIP enrichment (`source.geo.country_iso_code`, `destination.geo.country_name`).

**Problem**: FortiGate (and many other network devices) enrich traffic logs with GeoIP data — country codes, country names, and sometimes city/ASN info. The `network-fortigate` generator needed weighted country selection for both legitimate traffic (US/UK/DE/JP distributed by real CDN traffic patterns) and attack traffic (biased toward known scan/attack origins like CN/RU/KP). Currently this requires hardcoding country lists and weights inline in every template:

```jinja2
{%- set countries = [
  {"iso": "US", "name": "United States"},
  {"iso": "DE", "name": "Germany"},
  {"iso": "JP", "name": "Japan"},
  ... 15 more entries ...
] -%}
{%- set country_weights = [25, 8, 6, ...] -%}
{%- set country = module.rand.weighted_choice(countries, country_weights) -%}
```

This 20+ line block was duplicated across 3 templates (`traffic-forward-close`, `traffic-forward-deny`, `utm-ips`), each with slightly different weight distributions. The country data is identical — only the weights vary by context.

The same problem affects every network security generator: Check Point includes `origin_country`/`dst_country`, Palo Alto logs include `srccountry`/`dstcountry`, Cisco ASA includes geo fields, and ECS itself defines `source.geo.*` / `destination.geo.*` as standard fields.

**Proposal**: Add geographic data helpers to `module.rand`:

```python
module.rand.geo.country_code()          # → "US" (weighted by internet traffic share)
module.rand.geo.country_name()          # → "United States"
module.rand.geo.country()               # → {"iso": "US", "name": "United States"}
module.rand.geo.country_code(profile="attack")  # → biased toward scan origins
module.rand.geo.country_code(profile="cdn")     # → biased toward CDN traffic patterns
```

The `profile` parameter would select from pre-built weight distributions:

- `"traffic"` (default): weighted by global internet traffic (Cloudflare Radar data)
- `"attack"`: weighted by threat intelligence scan/attack origin data
- `"enterprise"`: weighted toward US/EU/JP for corporate traffic patterns

Implementation could use a simple dict of ISO 3166-1 alpha-2 codes with pre-computed weight arrays — ~200 lines of static data, zero external dependencies.

---

### 46. `module.rand.network.mac()` with OUI prefix support `[Low]`

**Context**: Building the `network-fortigate` generator where internal hosts have MAC addresses in sample data, and some templates generate dynamic MAC addresses for DHCP and ARP events.

**Problem**: `module.rand.network.mac()` generates a fully random MAC address. In reality, the first 3 octets (OUI — Organizationally Unique Identifier) identify the manufacturer. A realistic network has clusters of MACs from the same vendor (Dell servers share an OUI, HP workstations share another). The FortiGate generator worked around this by hardcoding MACs in the `internal_hosts.csv` sample, but any template needing a dynamic MAC (e.g., rogue device detection, DHCP events) produces unrealistically random OUIs.

FortiGate logs include `srcmac` and `dstmac` in DHCP events and `macaddr` in device detection. ECS maps these to `source.mac` / `destination.mac`. Other network generators (DNS, DHCP, switch logs) face the same issue.

**Proposal**: Extend `module.rand.network.mac()` with optional OUI prefix:

```python
module.rand.network.mac()                          # → fully random (current behavior)
module.rand.network.mac(oui="00:50:56")            # → VMware OUI + random suffix
module.rand.network.mac(vendor="dell")             # → random Dell OUI + random suffix
module.rand.network.mac(vendor="random_common")    # → weighted pick from top 20 OUIs
```

Include a small built-in table of ~20 common vendor OUI prefixes (Dell, HP, Lenovo, VMware, Cisco, Intel, Apple, etc.) for the `vendor` parameter. This would produce more realistic MAC distributions without requiring the generator author to hardcode OUI prefixes.

---

## Samples System

### 8. Samples: No support for weighted sampling `[High]`

**Problem**: When picking from sample data, `| random` gives uniform distribution. But in reality, some entries should be picked more often (e.g., `sshd` appears in 40% of auth events, `cron` in 15%). The workaround is `module.rand.weighted_choice()` with hardcoded lists, which bypasses the sample data entirely.

**Proposal**: Support an optional `weight` column in CSV samples or a `weight` field in JSON samples, then provide a `| weighted_random` filter:
```
{%- set u = samples.usernames | weighted_random -%}
```

---

### 19. Samples: No parameter interpolation in sample data files `[High]`

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

### 26. Samples: No render-time variable interpolation in sample data values `[Medium]`

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

### 18. Samples: No `selectattr` with multiple conditions in a single filter `[Medium]`

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

### 39. Samples: Inline data samples to eliminate external file dependency for small datasets `[Medium]`

**Context**: Building the `network-snort` generator where JSON sample named access doesn't work (proposal #33), forcing inline data in templates.

**Problem**: When JSON sample data can't be accessed by field name (tuples only — proposal #33), the workaround is inlining the data directly in each template as Jinja2 lists of dicts. For the Snort generator, 57 signatures were split across 13 templates (4–6 sigs each), resulting in ~300 lines of inline data that could have been a single 57-entry JSON file.

Even without the tuple limitation, small datasets (5–15 entries) that are only used by one template don't warrant a separate file. The overhead of creating a file, referencing it in `generator.yml` samples section, and loading it through tablib is disproportionate for inline-grade data.

**Example** — each of 13 Snort templates inlines its own signature list:

```jinja2
{#- Inline trojan-activity signatures (JSON samples don't support attribute access) -#}
{%- set sigs = [
  {"sid": 23493, "gid": 1, "rev": 6, "msg": "MALWARE-CNC Win.Trojan.ZeroAccess..."},
  {"sid": 40522, "gid": 1, "rev": 3, "msg": "MALWARE-CNC Unix.Trojan.Mirai..."},
  ...
] -%}
```

This works but scatters data across templates. A change to signature metadata requires finding and editing the right template file.

**Proposal**: Support inline sample data in `generator.yml` for small datasets:

```yaml
samples:
  internal_hosts:
    type: csv
    source: samples/internal_hosts.csv    # file-based for large datasets
    header: true
  trojan_sigs:
    type: inline                          # inline for small datasets
    data:
      - {sid: 23493, gid: 1, rev: 6, msg: "MALWARE-CNC Win.Trojan.ZeroAccess..."}
      - {sid: 40522, gid: 1, rev: 3, msg: "MALWARE-CNC Unix.Trojan.Mirai..."}
```

Templates would access inline samples identically to file-based ones: `samples.trojan_sigs | random`. This keeps data centralized in the config while avoiding file proliferation for small datasets. Combined with proposal #33 (named access), this would eliminate the need for inline Jinja2 data blocks entirely.

---

### 20. Samples: Pre-indexed grouping for O(1) filtered random access `[Low]`

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

## Shared State

### 4. Shared state: No built-in queue/pool abstraction `[High]`

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

### 3. Shared state: No atomic increment / counter primitive `[Medium]`

**Problem**: Every single template starts with `shared.get('sequence', 1000)` and ends with `shared.set('sequence', seq + 1)`. This is a very common pattern (monotonic record IDs, sequence numbers) but requires 2 lines of boilerplate in every template.

**Proposal**: Add `shared.increment('key', default=0, step=1)` that atomically gets and increments. Returns the pre-increment value. Saves 2 lines per template and eliminates the possibility of forgetting the final `shared.set()`.

---

### 44. Shared state: No pool utilization monitoring or overflow diagnostics `[Medium]`

**Context**: Building the `security-suricata` generator with two correlation pools (`flows` and `dns_queries`) serving 13 templates.

**Problem**: Correlation pools use shared state lists with manual capping (e.g., `if flows | length > 200: flows = flows[-200:]`). When the pool is always empty (consumers run faster than producers due to chance weight ratios), every consumer event falls back to standalone generation — effectively disabling correlation. When the pool overflows its cap, old entries are silently discarded.

In the Suricata generator, the `flows` pool is fed by 7 templates (DNS, HTTP, TLS, SSH, SMTP, fileinfo, alert) and consumed by 2 templates (flow-tcp, flow-udp). Whether the pool stays balanced depends on the chance weights, which may drift as the generator evolves. There's no way to know at a glance whether correlation is actually working at runtime — the 73% correlation rate I measured during testing was only discoverable by post-processing 1000 events with a custom Python script.

**Example diagnostic questions with no answer today**:
- "Is my `dns_queries` pool draining faster than it fills?" (→ most answers are uncorrelated)
- "Is my `flows` pool hitting its cap?" (→ entries are being dropped)
- "What's the average pool depth over the last 1000 events?" (→ no telemetry)

**Proposal**: Add optional pool diagnostics to shared state, either as:

1. **Structured logging**: When `--log-level debug`, log pool push/pop/overflow events:

   ```text
   DEBUG shared.pool 'flows' push: depth=42, cap=200
   DEBUG shared.pool 'flows' pop: depth=41
   WARN  shared.pool 'flows' overflow: depth=200, dropped=1
   ```

2. **Stats endpoint**: Expose pool utilization in the generator stats API (`GET /generators/{id}/stats`):

   ```json
   {"shared_pools": {"flows": {"depth": 42, "cap": 200, "total_pushed": 15000, "total_popped": 14958, "total_dropped": 0}}}
   ```

3. **Template-accessible stats**: `shared.pool_stats('flows')` returning a dict with `depth`, `push_count`, `pop_count`, `overflow_count` — enabling self-documenting templates that can log correlation health.

This would significantly reduce debugging time for correlation tuning, which is currently a blind trial-and-error process.

---

## Configuration & Validation

### 27. Config: No early validation of `${params.*}` / `${secrets.*}` references `[High]`

**Context**: Investigating the v2.0.2 bug where the API returned validation errors for configs with placeholders, and reviewing the config loading pipeline in `config_loader.py`.

**Problem**: When a generator config uses `${params.opensearch_host}` or `${secrets.api_key}`, there is no validation at startup that the referenced params and secrets actually exist. The substitution in `config_loader.py` only runs when the generator starts executing — which can be minutes after app startup. If a param is missing, the generator crashes with a `ValueError` at runtime. In multi-generator setups, one generator may start fine while another fails later due to a typo in a param name.

**Example**: A config references `${params.opensearch_host}` but `startup.yml` only defines `opensearch_url`. The app starts successfully, the generator begins processing, then crashes on first config load. The error message shows the missing key but offers no suggestion for the closest match.

**Proposal**: Add startup-time validation that cross-references all `${params.*}` and `${secrets.*}` tokens found in generator configs against the params defined in `startup.yml` and the secrets available in the keyring. Warn (or fail-fast with a `--strict` flag) if any references are unresolvable. Consider including "did you mean?" suggestions using edit distance for near-matches.

---

### 30. Config: No hot-reload for running generators `[Medium]`

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

## Developer Tooling / CLI

### 9. Template debugging: No dry-run or single-event mode `[High]`

**Problem**: When developing a new template, you iterate by running `eventum generate --live-mode` and eyeballing stdout. There's no way to render a single template once with fixed inputs to verify the JSON output. If a template has a Jinja2 syntax error, the error message points to the rendered output line, not the source template line.

**Proposal**: Add a `eventum render --template <path> --params <yaml>` command that renders a single template once with given params and prints the result. Include source-mapped error messages that point to the `.json.jinja` line number.

---

### 38. CLI: Output plugin selector for testing without config duplication `[High]`

**Context**: Building the `network-snort` generator with 13 templates and both stdout + opensearch outputs.

**Problem**: The standard generator config includes production outputs (OpenSearch, ClickHouse) alongside stdout for debugging. When testing during development, the production outputs fail because `${params.opensearch_host}` and `${secrets.opensearch_password}` aren't available — you're testing locally, not deploying. The generator crashes before rendering a single event.

The workaround is creating a separate `test-generator.yml` that duplicates the entire `event` section (params, samples, 13 template entries with chance weights) but only includes stdout in `output`. For the Snort generator, this meant maintaining a 75-line test config that was 90% identical to the 100-line production config. Any template addition required updating both files.

```yaml
# test-generator.yml — 75 lines, 90% duplicated from generator.yml
input:
  - cron:
      expression: "* * * * * *"
      count: 5

event:
  template:
    mode: chance
    params:
      # ... same 5 params ...
    samples:
      # ... same 3 samples ...
    templates:
      # ... same 13 templates with same weights ...

output:
  - stdout:                    # ← only difference
      formatter:
        format: json
```

**Proposal**: Add an `--only-output` CLI flag that selects which output plugins to activate:

```bash
# Only use stdout output, skip opensearch (no params/secrets needed)
eventum generate --path generator.yml --id test --only-output stdout

# Only use file output
eventum generate --path generator.yml --id test --only-output file
```

Implementation: after parsing the config, filter `GeneratorConfig.output` to only include plugins matching the specified name(s). Skip param/secret extraction for removed output blocks. This eliminates the need for separate test configs and keeps the single-source-of-truth pattern for generator definitions.

---

### 31. CLI: Config inspection command for discoverability `[Medium]`

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

### 11. Template composition: Document and promote `{% include %}` for reducing boilerplate `[Medium]`

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

## Operations / Reliability

### 28. Output: No retry or dead-letter mechanism for failed writes `[High]`

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

### 29. Generator: No lifecycle event hooks `[Medium]`

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

# 🔍 For Analysis

> Entries where the problem is clear but the right solution needs more research or discussion before committing to an approach.

---

## 6. Generator.yml: No way to express correlated template groups `[Critical]`

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

**Why analysis needed**: Major architectural change — introduces a new picking mode to the event plugin. Interaction with timestamps (should all steps share the same timestamp or be slightly offset?), error handling (what if one step in the sequence fails?), and compatibility with existing `chance`/`spin` modes needs investigation.

---

## 15. Template output: No JSON validation or structured output mode `[High]`

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

**Why analysis needed**: Multiple possible approaches — post-processing in the event plugin vs template-level filters (see #36). Performance impact of parsing JSON on every render at high EPS. Interaction with non-JSON output formats. Relationship with proposal #36 (template-level filter approach).

---

## 50. Template render skipping for consumer templates when correlation pool is empty `[High]`

**Context**: Building the `network-juniper-srx` generator where `session-close` consumes from a shared session pool populated by `session-create`.

**Problem**: Consumer templates (session-close, session-end, cred-disp, tunnel-disconnect) try to correlate with producer data from shared state pools. When the pool is empty — which happens at generator startup or when consumers fire faster than producers due to chance weight ratios — the consumer template falls back to generating standalone uncorrelated events.

In the Juniper SRX generator, the fallback in `session-close.json.jinja` generates a completely new session with different IPs, ports, policy, and session ID than any existing `session-create` event:

```jinja2
{%- if active_sessions | length > 0 -%}
  {%- set session = active_sessions.pop(0) -%}
  {# ... use correlated session data ... #}
{%- else -%}
  {# Fallback: generate standalone session-close with invented data #}
  {%- set src_ip = (samples.internal_hosts | random).ip -%}
  {%- set session_id = module.rand.number.integer(100000, 9999999) -%}
  {# ... 15 more lines of standalone data generation ... #}
{%- endif -%}
```

This produces "orphan" session-close events — sessions that appear to close without ever being opened. In real SRX traffic, every SESSION_CLOSE has a preceding SESSION_CREATE. Dashboards showing "sessions opened vs closed" or "session lifecycle" would immediately spot these anomalies.

The same problem affects every correlated generator: firewall session-start/end (content-packs has 4 generators with this pattern), Cisco VPN tunnel-established/disconnected, auditd USER_AUTH/CRED_ACQ pairs, and Suricata flow correlation. Each generator independently implements a 15-line fallback block that degrades data quality.

**Proposal**: Add a template-level skip mechanism that discards the current render and optionally re-picks another template:

Option A — declarative in `generator.yml`:
```yaml
templates:
  - session_close:
      template: templates/session-close.json.jinja
      chance: 400
      requires_shared: active_sessions   # skip if this shared key is empty/missing
```

Option B — imperative in templates:
```jinja2
{%- set active_sessions = shared.get('active_sessions', []) -%}
{%- if active_sessions | length == 0 -%}
  {%- do skip() -%}
{%- endif -%}
{%- set session = active_sessions.pop(0) -%}
```

When a template is skipped, the engine would either:
1. Discard the slot (reduce event count for this batch by 1), or
2. Re-run the chance picker and render a different template

Option 1 is simpler and preserves the overall event rate. Option 2 would shift the distribution slightly toward non-consumer templates when pools are empty, which is actually more realistic (if there are no open sessions, there should be fewer close events).

This would eliminate the entire class of fallback-generated orphan events and the ~15 lines of fallback boilerplate per consumer template, while improving correlation accuracy from ~70-80% to 100% for pool-based patterns.

**Why analysis needed**: Two fundamentally different approaches (declarative vs imperative). Skip behavior (discard slot vs re-pick) has different trade-offs for event rate and distribution. Interaction with proposal #6 (sequence mode) — if sequences are implemented, the skip pattern may be less needed.

---

## 21. Event plugin: Burst/fan-out mode for correlated multi-event groups `[Medium]`

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

**Why analysis needed**: Complex interaction with the event pipeline — bursts produce variable event counts per trigger, which affects batch sizing, timestamp assignment (should burst events share a timestamp or be slightly spread?), and throughput calculations. Overlaps with proposal #6 (sequence mode); a unified "multi-event emission" design may be better than two separate features.

---

## 47. Template variable extraction/sharing via `{% set_shared %}` for cross-template header deduplication `[Medium]`

**Context**: Building the `network-fortigate` generator with 12 templates that all start with the same 4-line parameter extraction block.

**Problem**: All 12 FortiGate templates begin with identical boilerplate extracting common variables from `params`:

```jinja2
{%- set hostname = params.hostname -%}
{%- set fqdn = hostname ~ '.' ~ params.domain -%}
{%- set devid = params.serial_number -%}
{%- set vd = params.get('vdom', 'root') -%}
```

And all 12 end their JSON with an identical `observer` block:

```json
"observer": {
    "name": "{{ hostname }}",
    "product": "Fortigate",
    "serial_number": "{{ devid }}",
    "type": "firewall",
    "vendor": "Fortinet"
}
```

This is 4 + 7 = 11 lines duplicated × 12 templates = 132 lines of pure boilerplate. Proposal #11 addresses this with `{% include %}`, but includes have a limitation: included fragments can't define variables that the caller then uses in its own body (variables set inside an `{% include %}` are scoped to the include). You'd need `{% extends %}` with blocks, which requires restructuring all templates into a base+child pattern — a heavy refactor for what should be a simple "compute these 4 values once."

Note: Proposal #11 focuses on `{% include %}` for *output fragments* (shared JSON blocks). This proposal addresses a different pattern: *computed variable sharing* — defining variables once that all templates can reference without each template re-deriving them.

**Proposal**: Support a `computed_vars` or `globals` section in the template plugin config that defines Jinja2 expressions evaluated once per render and injected into every template's namespace:

```yaml
event:
  template:
    mode: chance
    params:
      hostname: fw-edge-01
      domain: corp.example.com
      serial_number: FGT60F0000000001
    computed:
      hostname: "{{ params.hostname }}"
      fqdn: "{{ params.hostname }}.{{ params.domain }}"
      devid: "{{ params.serial_number }}"
      vd: "{{ params.get('vdom', 'root') }}"
    templates:
      - ...
```

Templates would then directly use `{{ hostname }}`, `{{ fqdn }}`, `{{ devid }}`, `{{ vd }}` without the extraction block. This eliminates the header boilerplate across all templates and ensures consistency (if the derivation logic changes, it changes in one place).

**Why analysis needed**: Overlaps with proposal #11 (`{% include %}` for fragments). The `computed` approach adds a new config concept and evaluation phase. Need to decide whether `computed` expressions can reference each other (dependency ordering), whether they can use `module.*` and `samples.*`, and how they interact with the existing `params` namespace.

---

## 36. Template API: No `| tojson_value` filter for conditional JSON field emission `[Medium]`

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

**Why analysis needed**: Two very different approaches — surgical per-field filter vs whole-output post-processing. Relationship with proposal #15 (format: json mode) which provides a more comprehensive solution at the plugin level. The right approach depends on whether #15 is implemented.

---

## 10. Generator.yml: `count` in input doesn't scale with template count `[Low]`

**Problem**: `count: 5` means 5 events per second total, distributed across all templates by chance weight. When you add more event types, you may want to increase the count proportionally. There's no way to say "I want ~2 SYSCALL events per second and ~1 auth event per second" without manual weight math.

**Proposal**: Consider supporting per-template rate targets in addition to global count, or document the relationship between `count`, `chance` weights, and expected per-type throughput more clearly.

**Why analysis needed**: Two very different approaches — per-template rate targets (new feature, changes the input→event interface) vs better documentation (zero code change). Per-template rates would also interact with proposal #6 (sequence mode) and #21 (burst mode) where event counts are variable.

---

## 5. Samples: No way to pick a random row and keep it as a flat dict `[Low]`

**Problem**: CSV samples accessed as `(samples.usernames | random)` return a row object. When you need multiple fields from the same row, you must store the whole row first (`{%- set u = samples.usernames | random -%}`) and then access fields individually. This is fine, but there's no way to destructure or spread a sample row into the template namespace.

**Proposal**: Consider a `| spread` or `| unpack` Jinja2 filter that sets multiple variables from a dict at once — or document the recommended pattern more prominently.

**Why analysis needed**: Two very different approaches — a `| spread` filter (Jinja2 doesn't natively support setting variables from filters, would need a custom extension) vs documentation (the `{%- set u = ... -%}` pattern works fine). The filter approach may not even be feasible within Jinja2's evaluation model.

---

## 51. 🆕 Feature: CLI `--max-events N` flag for bounded test generation

**Context**: Building the `network-paloalto-url` generator and validating output.

**Problem**: When testing a generator during development, there's no way to generate exactly N events and stop. The cron input plugin fires indefinitely in both live and sample mode, so the only way to get bounded output is `timeout X eventum generate ...`. This sends SIGTERM mid-execution, which truncates the last event — producing an invalid JSON line. Piping to `jq` or `python -m json.tool` fails on the partial final line. The alternative is capturing to a file and discarding the last line, which is fragile.

**Example from the PAN-OS URL Filtering generator**: To analyze the action distribution, the workflow was:

```bash
timeout 5 uv run eventum generate ... > /tmp/events.jsonl
# Last line is always truncated: "Unterminated string starting at char 1826"
python3 -c "...json.loads(line)..." # Must handle the truncated line
```

The `--batch.size` flag controls how many events are processed per batch but doesn't limit total count. There's no way to say "generate 1000 events and exit cleanly."

**Proposal**: Add a `--max-events N` CLI flag that cleanly stops generation after exactly N events are written to all outputs:

```bash
eventum generate --path generator.yml --id test --live-mode false --max-events 1000
```

Implementation: add a counter to the executor that tracks total events written. After reaching the limit, signal the generator to stop gracefully (drain current batch, close output plugins, exit). This ensures the last event is complete and all outputs are properly flushed.

This would eliminate the `timeout` + truncated-line workaround that every generator developer hits during testing.

---

## 52. 🆕 Feature: `| url_components` filter for URL decomposition in templates

**Context**: Building the `network-paloalto-url` generator where ECS requires separate `url.domain`, `url.path`, `url.query`, and `url.extension` fields.

**Problem**: URL Filtering and web proxy generators need to decompose URLs into their ECS components (`url.domain`, `url.path`, `url.query`, `url.extension`). Currently the workarounds are:

1. **Pre-decompose in sample data** (used in this generator): Store `domain` and `path` as separate fields in `url_categories.json`, forcing a nested structure and doubling the sample data size vs. a flat URL string list.

2. **Use `module.urllib.parse`** (verbose and error-prone in Jinja2):

   ```jinja2
   {%- set parsed = module.urllib.parse.urlparse("https://" ~ url_string) -%}
   {%- set url_domain = parsed.hostname -%}
   {%- set url_path = parsed.path -%}
   {%- set url_query = parsed.query -%}
   ```

Neither approach is clean. The pre-decomposition inflates sample files and forces URL authors to manually split URLs. The `urlparse` approach requires prepending a scheme (PAN-OS URLs are schemeless like `www.google.com/search?q=test`) and produces attribute access that's fragile across Python versions.

**Proposal**: Add a `| url_components` Jinja2 filter that returns a dict of URL parts, handling schemeless URLs:

```jinja2
{%- set url = "www.google.com/search?q=test" | url_components -%}
{{ url.domain }}     → "www.google.com"
{{ url.path }}       → "/search"
{{ url.query }}      → "q=test"
{{ url.extension }}  → ""
{{ url.original }}   → "www.google.com/search?q=test"
```

This would allow flat URL strings in sample data (`"urls": ["www.google.com/search?q=test"]`) instead of nested objects, reducing sample file size and complexity. Useful for any web traffic generator: PAN-OS URL Filtering, proxy logs, web server access logs, WAF events.

---

## 53. 🆕 Feature: Per-template variables (`vars`) for parameterized template reuse `[High]`

**Context**: Building the `network-cisco-asa` generator with 14 templates covering TCP/UDP/ICMP connection built/teardown, NAT built/teardown, and other event categories.

**Problem**: The Cisco ASA generator has 3 "connection built" templates (`302013-tcp-built`, `302015-udp-built`, `302020-icmp-built`) and 3 "connection teardown" templates (`302014-tcp-teardown`, `302016-udp-teardown`, `302021-icmp-teardown`). These 6 files are ~80% identical in structure — same connection ID counter, same direction selection, same host lookups, same NAT logic, same JSON output structure. The only differences are:

- Protocol name (`tcp`/`udp`/`icmp`) and IANA number (`6`/`17`/`1`)
- Message ID (`302013`/`302015`/`302020`)
- Pool name (`tcp_sessions`/`udp_sessions`/`icmp_sessions`)
- Protocol-specific fields (TCP has teardown reasons and bytes, ICMP has type/code)

Currently, all templates share the same `params` dict — there's no way to pass per-entry variables. This means each protocol variant requires a separate template file even when 120+ lines are identical. In the ASA generator, the TCP built (153 lines) and UDP built (148 lines) templates share ~130 lines verbatim. Multiplied across built+teardown pairs, this is ~400 lines of pure duplication.

The same pattern affects NAT templates (`305011-nat-built` and `305012-nat-teardown` share structure with connection templates) and appears in other generators: `network-checkpoint` has separate templates for accept/drop/reject that share 90% of their JSON structure, and `network-firewall` has protocol-variant session templates.

Note: Proposal #47 addresses *global* computed variables shared by all templates. This proposal addresses *per-entry* variables that differ between template entries pointing to the same `.jinja` file — enabling template reuse rather than just variable sharing.

**Proposal**: Add an optional `vars` (or `template_vars`) section to each template entry in `generator.yml` that injects entry-specific variables into the template's namespace:

```yaml
templates:
  # One template file serves all three protocols
  - tcp_built:
      template: templates/connection-built.json.jinja
      chance: 220
      vars:
        protocol: tcp
        iana_number: "6"
        message_id: "302013"
        pool_name: tcp_sessions
        pool_cap: 200
  - udp_built:
      template: templates/connection-built.json.jinja    # same file!
      chance: 75
      vars:
        protocol: udp
        iana_number: "17"
        message_id: "302015"
        pool_name: udp_sessions
        pool_cap: 200
  - icmp_built:
      template: templates/connection-built.json.jinja    # same file!
      chance: 15
      vars:
        protocol: icmp
        iana_number: "1"
        message_id: "302020"
        pool_name: icmp_sessions
        pool_cap: 50
```

The template would access these via `{{ vars.protocol }}` or a merged namespace:

```jinja2
{#- Protocol-agnostic connection built template -#}
{%- set sessions = shared.get(vars.pool_name, []) -%}
...
"network": {
    "iana_number": "{{ vars.iana_number }}",
    "transport": "{{ vars.protocol }}"
},
```

This would collapse the ASA generator's 6 connection templates (TCP/UDP/ICMP × built/teardown) into 2 parameterized templates, eliminating ~400 lines of duplication. The pattern would benefit every generator that has protocol or event-type variants sharing a common structure.

Implementation: in the template plugin, merge `vars` into the render context alongside `params`, `samples`, `shared`, `timestamp`, and `module`. The `vars` dict would be a flat key-value map (no Jinja2 expression evaluation needed — just YAML scalars).

---

## 54. 🆕 Feature: Document and warn about `| tojson` requirement for `event.original` syslog fields `[Medium]`

**Context**: Building the `network-cisco-asa` generator where every template constructs an `event.original` syslog line containing the raw ASA message.

**Problem**: The `event.original` field in ECS contains the raw log line as received by the collector. For syslog-based generators, this means building a string like `"Feb 21 2026 14:30:15 ASA-FW-01 : %ASA-4-106023: Deny tcp src outside:203.0.113.5/52847 dst inside:10.1.1.10/443 by access-group \"OUTSIDE_IN\" [0xa1b2c3d4, 0x0]"`. The natural template pattern is:

```jinja2
{%- set original_msg = "%ASA-4-106023: Deny " ~ protocol ~ " ... by access-group \"" ~ rule.name ~ "\" [" ~ hash1 ~ ", " ~ hash2 ~ "]" -%}
...
"original": "{{ timestamp.strftime('%b %d %Y %H:%M:%S') }} {{ hostname }} : {{ original_msg }}"
```

This **silently produces invalid JSON** because the escaped quotes (`\"`) in the Jinja2 string become literal `"` in the rendered output, breaking the JSON string boundary. The error manifests as a runtime JSON parse failure (`"JSON is malformed: expected ',' or '}' (byte 678)"`) with no indication of which field or template caused it.

In the ASA generator, this bug appeared in the `106023-acl-deny` template where ACL names are quoted in real ASA syslog output (e.g., `access-group "OUTSIDE_IN"`). The fix required switching to a non-obvious pattern:

```jinja2
{%- set full_original = timestamp.strftime('%b %d %Y %H:%M:%S') ~ " " ~ hostname ~ " : " ~ original_msg -%}
"original": {{ full_original | tojson }},
```

Key insight: `{{ var | tojson }}` (without surrounding double quotes) properly JSON-escapes the string *and* adds the enclosing quotes. This is fundamentally different from `"{{ var }}"` which does not escape inner quotes.

This pattern is needed by every syslog-based generator (6+ in content-packs: Cisco ASA, FortiGate, Check Point, auditd, Snort, Suricata) because real syslog messages routinely contain characters that break JSON: double quotes around identifiers, backslashes in Windows paths, control characters in error messages.

Note: Proposal #15 addresses post-processing JSON validation (parsing and fixing output). Proposal #36 addresses conditional field emission with safe comma handling. This proposal addresses a different gap: the **construction-time** pattern of safely embedding arbitrary strings into JSON string fields — specifically the non-obvious `{{ var | tojson }}` vs `"{{ var }}"` distinction.

**Proposal**: Two complementary improvements:

1. **Documentation**: Add a "JSON String Safety" section to the template API docs with a clear rule: *"For any string field that may contain quotes, backslashes, or control characters, use `{{ var | tojson }}` without surrounding quotes instead of `"{{ var }}"`."* Include a before/after example showing the `event.original` syslog case.

2. **Lint warning**: When `format: json` (#15) is eventually implemented, detect the pattern `"{{ ... }}"` where the rendered value contains unescaped `"` and emit a warning pointing to the field name and suggesting `| tojson`. This would catch the bug at render time instead of at JSON parse time, with a fix suggestion instead of an opaque byte offset.

```text
WARNING: Field "event.original" contains unescaped double quote at position 45.
  Hint: Use {{ full_original | tojson }} instead of "{{ original_msg }}" for safe JSON embedding.
```

---

## 55. 🆕 Feature: Output plugin `optional` flag for graceful degradation when params/secrets are unavailable `[High]`

**Context**: Building the `network-netflow` generator with both stdout and OpenSearch outputs in the same `generator.yml`.

**Problem**: Content-pack generators include both a development output (stdout) and a production output (OpenSearch/ClickHouse) in the same config. The production output uses `${params.*}` and `${secrets.*}` placeholders:

```yaml
output:
  - stdout:
      formatter:
        format: json
  - opensearch:
      hosts:
        - ${params.opensearch_host}
      username: ${params.opensearch_user}
      password: ${secrets.opensearch_password}
      index: ${params.opensearch_index}
```

When running locally for development/testing, the config loader attempts to resolve ALL `${params.*}` and `${secrets.*}` tokens across the entire config — including outputs that the user doesn't intend to use. If the opensearch params aren't provided via `--params` or `startup.yml`, or the keyring doesn't have the secret, the generator crashes before rendering a single event.

In the NetFlow generator, testing required:

1. Passing `--params '{"opensearch_host": "...", "opensearch_user": "...", "opensearch_index": "..."}'` with dummy values
2. Creating a fresh keyring file with a dummy `opensearch_password` secret
3. Passing `--cryptfile /tmp/test_keyring.cfg` with the correct env var `EVENTUM_KEYRING_PASSWORD`
4. Tolerating connection-refused errors from the opensearch output in the logs

All of this ceremony just to see stdout output. Every content-pack generator has this same pattern — both stdout and opensearch in the config — and every developer hits this friction when testing locally.

Note: Proposal #38 addresses this with a CLI-level `--only-output stdout` flag that filters outputs before config loading. This proposal addresses a complementary approach: a config-level declaration that makes an output plugin degrade gracefully without requiring the user to remember CLI flags.

**Proposal**: Add an `optional: true` flag to output plugin config that makes the plugin silently skip initialization when its params/secrets can't be resolved:

```yaml
output:
  - stdout:
      formatter:
        format: json
  - opensearch:
      optional: true    # Skip if params/secrets unavailable
      hosts:
        - ${params.opensearch_host}
      username: ${params.opensearch_user}
      password: ${secrets.opensearch_password}
      index: ${params.opensearch_index}
```

When `optional: true` and the config loader encounters unresolvable `${params.*}` or `${secrets.*}` tokens in that output block, it should:

1. Log a notice: `Output 'opensearch' skipped: missing param 'opensearch_host'`
2. Remove the output from the active pipeline
3. Continue with remaining outputs

This differs from #38 in several ways:

- **No CLI flag needed** — the config itself declares which outputs are optional
- **Self-documenting** — reading the config tells you which outputs are required vs nice-to-have
- **Content-pack friendly** — generator authors can mark production outputs as optional in the distributed config, so end users can test immediately without setup
- **Composable with #38** — `--only-output` is imperative (user decides at runtime); `optional` is declarative (author decides at design time). Both are useful.

Implementation: in `config_loader.py`, during `${params.*}` / `${secrets.*}` resolution, catch `MissingParam`/`MisssingSecret` errors per output block. If the block has `optional: true`, log and remove it from `GeneratorConfig.output`. Otherwise, raise as today.

---

# ✅ Completed

## 32. Bug: Stdout output plugin crashes with `writelines` — `NonFileStreamWriter` incompatibility

**Status**: Fixed. Replaced `self._writer.writelines(lines)` with a loop using `self._writer.write(line)` in `stdout/plugin.py`.

---

## 33. Samples: Rows are plain tuples — no named field access despite headers/keys

**Status**: Fixed. Wrapped rows in `namedtuple` (with `rename=True`) in `Sample.__init__` when headers exist. Both index and named access now work.

---

## 34. Config: `${params.*}` tokens extracted from YAML comments cause false-positive missing-params errors

**Status**: Fixed. Added `_strip_yaml_comments()` preprocessing in `config_loader.py` before token extraction.

---

## 35. Samples: JSON sample loading crashes with unhelpful error on heterogeneous schemas

**Status**: Fixed. Caught `InvalidDimensions` from tablib and re-raised as `SampleLoadError` with clear "inconsistent keys" message.

---

## 56. 🆕 Feature: `| zfill(N)` filter for zero-padded numeric strings `[Medium]`

**Context**: Building the `fortinet-fortimail` generator with type-prefixed monotonic log IDs (10-digit zero-padded: `0200004500`, `0003001234`, `0300000901`).

**Problem**: Jinja2 has no built-in zero-padding filter. The only workaround is a string-slice hack that prepends zeros and takes the last N characters:

```jinja2
{%- set log_id = "02" ~ ("00000000" ~ (stats_log_seq | string))[-8:] -%}
{%- set seq_str = ("000000" ~ (session_seq | string))[-6:] -%}
```

This pattern appears **10+ times** across the 12 FortiMail templates — for statistics log IDs (`02XXXXXXXX`), SMTP event IDs (`0003XXXXXX`), spam log IDs (`0300XXXXXX`), virus log IDs (`0100XXXXXX`), kevent IDs (`0701XXXXXX`/`0704XXXXXX`), and 6-digit session sequence numbers. It's also used in the windows-security generator for process IDs and logon IDs, in network-fortigate for log IDs, and in any generator that needs fixed-width numeric identifiers.

The hack is fragile — if the number exceeds the padding width, the slice silently truncates the leading digits instead of producing a wider string. It's also non-obvious to read: `("000000" ~ (n | string))[-6:]` requires mental parsing to understand "zero-pad to 6 digits."

**Proposal**: Register a custom `zfill` filter (named after Python's `str.zfill()`):

```python
# In template environment setup:
env.filters['zfill'] = lambda s, width: str(s).zfill(width)
```

Usage in templates:

```jinja2
{%- set log_id = "02" ~ (stats_log_seq | zfill(8)) -%}
{%- set seq_str = session_seq | zfill(6) -%}
```

One line of Python, eliminates a fragile 30-character expression repeated across every generator that uses numeric IDs.

---

## 57. 🆕 Feature: JSON sample loading should support dict/mapping format for grouped data `[Medium]`

**Context**: Building the `fortinet-fortimail` generator with 60 email subjects across 5 categories (business, automated, newsletter, spam, phishing).

**Problem**: The natural JSON structure for categorized sample data is a dict mapping category names to arrays:

```json
{
    "business": ["Q4 Financial Report", "Meeting Agenda", ...],
    "spam": ["Congratulations! You have won", ...],
    "phishing": ["Urgent: Verify your account", ...]
}
```

This format is rejected by the JSON sample reader because tablib requires an array of objects. The forced workaround is restructuring into a flat array with a category field:

```json
[
    {"category": "business", "text": "Q4 Financial Report"},
    {"category": "spam", "text": "Congratulations! You have won"},
    ...
]
```

And then using a verbose `selectattr` filter chain in every template that needs a category-specific entry:

```jinja2
{%- set subject = (samples.subjects | selectattr("category", "equalto", "spam") | list | random).text -%}
```

This 90-character expression replaces what would be `samples.subjects.spam | random` with a dict format. It's also O(n) per render (scans all 60 entries to find matching category), whereas a dict lookup would be O(1).

Note: Proposal #20 (`index_by`) addresses this from the config side — grouping an array at load time. This proposal addresses it from the data side — supporting dict-format JSON natively without needing a tablib Dataset intermediary.

**Proposal**: When a JSON sample file contains a top-level dict (not an array), expose it directly as a dict of lists. If the values are arrays of strings, wrap them as single-field objects for consistency. If the values are arrays of objects, expose them as-is:

```python
# In SamplesReader._load_json_sample():
if isinstance(data, dict):
    # Expose as grouped sample: samples.subjects.spam → list of items
    return GroupedSample(data)
```

Template access:

```jinja2
{%- set subject = samples.subjects.spam | random -%}
{%- set virus = samples.viruses | random -%}    {# array format still works #}
```

This would be complementary to #20 (`index_by`): dict format is for data that is *authored* as grouped (categories known at authoring time); `index_by` is for data that is *stored* flat but *accessed* grouped (categories discovered at load time).

---

## 58. 🆕 Feature: `module.rand.string.pattern()` for formatted random strings `[Medium]`

**Context**: Building the `fortinet-fortimail` generator where every email event has an authentically formatted session ID: `[7 letters][char][6-digit seq]-[7 letters][char][6-digit seq]`.

**Problem**: Generating a FortiMail session ID requires 5 lines of template code:

```jinja2
{%- set pfx = module.rand.string.letters(7) -%}
{%- set c1 = module.rand.choice("abcdefghijkmnpqrstuvwxyz") -%}
{%- set c2 = module.rand.choice("bcdefghjkmnpqrstuvwxyz") -%}
{%- set seq_str = ("000000" ~ (session_seq | string))[-6:] -%}
{%- set session_id = pfx ~ c1 ~ seq_str ~ "-" ~ pfx ~ c2 ~ seq_str -%}
```

This exact 5-line block is **copy-pasted across 7 templates** (5 statistics, 1 SMTP receive, 1 spam-detection fallback). Any format change (e.g., fixing the sequence width or adding uppercase letters) requires editing all 7 copies.

Similar multi-step random string construction appears in other generators: Windows Security's logon IDs (`0x` + 8 hex chars), Sysmon's process GUIDs (`{` + uuid + `}`), FortiGate's session IDs, and Checkpoint's log UIDs.

Note: Proposal #11 (`{% include %}`) addresses this from the template composition side — extracting shared fragments into partials. This proposal addresses it from the API side — providing a one-line way to generate formatted random strings without needing includes or macros.

**Proposal**: Add `module.rand.string.pattern(format_string)` that generates a random string from a mini-DSL:

```python
# Format specifiers:
#   %a = lowercase letter    %A = uppercase letter    %l = letter (any case)
#   %d = digit               %h = hex char            %x = hex char (lower)
#   Literal characters are preserved
#   {N} after a specifier = repeat N times

module.rand.string.pattern("%a{7}%a%d{6}-%a{7}%a%d{6}")
# → "qJgHmRbk003642-qJgHmRbv003642"

module.rand.string.pattern("0x%h{8}")
# → "0x3F7A1B2E"

module.rand.string.pattern("{%l{8}-%l{4}-%l{4}-%l{4}-%l{12}}")
# → "{a1b2c3d4-e5f6-7890-abcd-ef1234567890}"
```

Usage in templates:

```jinja2
{%- set session_id = module.rand.string.pattern("%a{7}%a" ~ (session_seq | zfill(6)) ~ "-%a{7}%a" ~ (session_seq | zfill(6))) -%}
```

This reduces 5 lines to 1 line and makes the format self-documenting. For purely random strings (no counter interpolation), it's even simpler:

```jinja2
{%- set logon_id = module.rand.string.pattern("0x%H{8}") -%}
```

Implementation: ~30 lines of Python using `re.sub` to replace format specifiers with random characters from the appropriate character set.

---

## 42. Bug: CSV sample parser doesn't handle quoted fields with commas (RFC 4180 violation)

**Status**: Fixed. Tablib already uses Python's `csv.reader` which handles RFC 4180 quoting correctly. Added explicit `quotechar` config option to `CSVSampleConfig` (passed through to tablib), caught `InvalidDimensions` with a helpful `SampleLoadError` including file path and RFC 4180 hint, added `quotechar` to Zod schema and Studio UI, and documented the parameter.

---

## 59. 🐛 Bug: CLI `--live-mode` uses non-standard boolean flag syntax `[Low]`

**Status**: Fixed. Modified `_create_option()` in `pydantic_converter.py` to detect `bool` fields and generate standard Click boolean flag pairs (`--flag/--no-flag`). All boolean CLI options (`--live-mode`, `--skip-past`, `--keep-order`) now follow the Click convention.
