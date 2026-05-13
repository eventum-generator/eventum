---
name: market-radar
description: Use when scanning what competitors and adjacent tools are shipping or discussing - to surface trends worth adopting and popular topics Eventum can credibly join for audience growth.
---

# Market Radar

Periodic market scan with two outputs:

1. **Observations** - what's shipping and trending across the space.
2. **Opportunities** - for themes fitting Eventum, a feature angle and an engagement angle.

## When to use

- Periodic sweep at planning cycle start.
- Checking whether a feature idea already exists in the wild.
- Backlog grooming - seeing what's gaining traction elsewhere.
- Finding active conversations where Eventum can credibly grow its audience.

## Scope

**Domains** - scan all; empty domains are a valid finding:

- Synthetic data and log generators.
- SIEM and log management platforms.
- Event streaming and data movers.
- Load and chaos tools - test-data and scenario generation features, not load orchestration.
- Observability pipelines - agents and collectors for metrics, logs, traces.

**Signals**:

- New plugins, integrations, or output formats from competitors.
- Features repeatedly requested or praised in community channels.
- Patterns recurring across vendors' changelogs.
- Noteworthy SIEM, observability, or data conference talks.
- User pain points surfacing across multiple tools.
- Momentum topics - subjects with disproportionate attention right now.

**Ignore**: pricing and commercial strategy, one-off niche releases without broader signal, marketing rebrands that do not change capability.

## Sources

At minimum: GitHub (trending, releases, Discussions), HN, Reddit (r/devops, r/cybersecurity, r/sre, r/dataengineering), Product Hunt, vendor changelogs and engineering blogs, public conference recordings and slides.

## Process

1. **Scan** domains in parallel. Cast a wide net beyond known vendors - discovering emerging tools is a core goal. Collect up to 10 items per domain, each with: one-sentence description, source with link, date, signal strength (stars, reactions, adoption count, or "multiple vendors shipped similar"), and whether it's a new idea or iteration. Record "nothing notable" explicitly when a domain is empty.

2. **Consolidate**:
   - Group similar items into themes (e.g. "three vendors added OTLP output", "multiple tools now ship ECS-native templates").
   - Rank themes by combined signal - contributing vendors, total engagement, recurring vs isolated.

3. **Opportunities** - only for themes with plausible fit with Eventum.
   - **Feature angle** - one line on what Eventum could build, polish, or expose, plus 2-3 bullets (user value, rough effort, overlap with existing plugins or generators).
   - **Engagement angle** - one line on how Eventum could contribute to the conversation, plus 2-3 bullets (talking point, candidate channel such as Habr/Dev.to/Reddit/HN/CFP, existing Eventum capability that makes the contribution credible).

4. **Report**:
   - 5-10 themes, highest signal first.
   - Each theme: one-paragraph summary, 2-3 representative examples with links and dates, one line noting whether Eventum already covers it.
   - Feature and engagement angle blocks for qualifying themes.
   - Explicit "nothing notable" list for empty domains.

## Rules

- Public sources only; no screenshots or hearsay.
- Closed-source vendors are in scope when the feature is publicly documented (docs, release notes, engineering blog, conference talk).
- Engagement angles require a credible hook - do not recommend joining a conversation where Eventum has nothing real to contribute.
- Output stops at the angle level - no blog drafts, content calendars, or platform-specific copy; artifact creation is delegated to other workflows.
