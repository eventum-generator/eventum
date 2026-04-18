---
name: market-radar
description: Use when scanning what competitors and adjacent tools are shipping or discussing - to surface trends worth adopting and popular topics Eventum can credibly join for audience growth.
---

# Market Radar

Periodic market scan with two outputs:

1. **Observations** - what's shipping, what's trending, what's repeatedly discussed across the space.
2. **Opportunities** - for themes with plausible fit, a feature angle (what to build or polish) and an engagement angle (how Eventum could contribute to the conversation to grow its audience in the space).

## When to use

- Periodic sweep at the start of a quarter or planning cycle.
- Checking whether a feature idea already exists in the wild and in what form.
- Backlog grooming - seeing which capabilities are gaining traction elsewhere.
- Finding active conversations where Eventum can credibly grow its audience - topics getting disproportionate attention in the space.

## Scope

**Domains** - scan across all of these; "nothing notable" is a valid outcome for quiet domains:

- Synthetic data and log generators - tools that produce fake, sampled, or simulated data, events, or logs for testing, training, or seeding systems.
- SIEM and log management platforms - solutions that ingest, store, search, and alert on security or operational logs.
- Event streaming and data movers - systems that route, transform, and deliver events between sources and sinks.
- Load and chaos tools - test harnesses that generate load, inject faults, or drive scenarios. Focus on their test-data and scenario generation features, not load orchestration.
- Observability pipelines - agents and collectors that gather, process, and forward telemetry (metrics, logs, traces).

**Signals to collect**:

- New plugins, integrations, or output formats shipped by competitors.
- Features repeatedly requested or praised in community channels.
- Patterns recurring across multiple vendors' changelogs.
- Noteworthy talks from SIEM, observability, or data conferences.
- User pain points that keep surfacing across tools.
- Momentum topics - subjects with disproportionate attention and activity right now (HN front page, Reddit hot, recurring conference themes, sustained community chatter).

**Ignore**:

- Pricing and commercial strategy.
- One-off niche releases without broader signal.
- Marketing rebrands that do not change capability.

## Sources

Draw from at minimum:

- GitHub - trending repos, release feeds, Discussions.
- HN - Show HN threads and recent front-page items in the domain.
- Reddit - subreddits such as r/devops, r/cybersecurity, r/sre, r/dataengineering.
- Product Hunt - launches in the data/observability/security categories.
- Vendor changelogs and engineering blogs.
- Conference recordings or slide decks when publicly available.

## Process

1. **Scan** each domain. Domains are independent - run scans in parallel when possible. Cast a wide net per domain: include both established leaders and newer or less-visible entrants. Do not anchor the scan to a preset list of vendors - discovery of emerging tools is a core goal. For each domain, collect up to 10 items shaped as:

   - One-sentence description.
   - Who ships or published it, with a link.
   - Date of release or publication.
   - Signal strength - stars, reactions, adoption count, or "multiple vendors shipped similar".
   - Whether it is a new idea or an incremental iteration.

   If a domain has nothing worth reporting, record that explicitly instead of padding.

2. **Consolidate** the raw findings:

   - Drop items outside Eventum's niche (synthetic event generation for SIEM and observability test data).
   - Group similar items into themes - e.g. "three vendors added OTLP output", "multiple tools now ship ECS-native templates".
   - Rank themes by combined signal - number of contributing vendors, total engagement, whether it is recurring or isolated.

3. **Opportunities** - only for themes with plausible fit with Eventum. Skip the rest; forced recommendations are worse than no recommendations. For each qualifying theme:

   - **Feature angle** - one line on what Eventum could build, polish, or expose to match the theme, plus 2-3 bullets justifying it (user value, rough effort, overlap with existing plugins or generators).
   - **Engagement angle** - one line on how Eventum could contribute to the conversation, plus 2-3 bullets (talking point, candidate channel such as Habr/Dev.to/Reddit/HN/conference CFP, what existing Eventum capability lets us credibly contribute).

4. **Report** to the user:

   - 5-10 themes, highest signal first.
   - Each theme: one-paragraph summary, 2-3 representative examples with links and dates, one line noting whether the theme is already covered by Eventum.
   - For qualifying themes: feature angle block and engagement angle block as defined above.
   - Explicit "nothing notable" list for domains that came back empty.

## Rules

- Observational first, actionable second - a theme without plausible fit stays observational only.
- Public sources only; do not infer from screenshots or hearsay.
- Closed-source vendors are in scope when the feature is publicly documented - docs, release notes, engineering blog, or conference talk.
- Cite every item with a link and a date.
- Empty domains are a valid finding - do not pad.
- No full blog drafts, no content calendars, no platform-specific copy - recommendations end at the angle level; artifact creation is delegated to other workflows.
- Engagement angles require a credible hook - do not recommend joining a conversation where Eventum has nothing real to contribute.
