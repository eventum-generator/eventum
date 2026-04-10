---
name: growth-review
description: Analyze Eventum's market position, competitive landscape, and growth opportunities. Produce actionable strategy recommendations and a content plan.
user-invokable: true
argument-hint: "[focus-area] (e.g. competitive, features, community, or omit for full review)"
context: fork
---

## Current state
- GitHub stars: !`gh api repos/eventum-dev/eventum --jq '.stargazers_count'`
- Open issues: !`gh issue list --limit 5 --json number,title`
- Recent releases: !`gh release list --limit 3`

## Growth Review

Orchestrate a strategic review of Eventum's market position and growth opportunities by delegating to your team of agents.

Parse the optional argument as the focus area. If omitted, perform a full review covering all areas.

### Phase 1: Market Scan

**Delegate to product-strategist agent**:

- Research the competitive landscape:
  - Direct competitors (synthetic data/event generation tools)
  - Adjacent tools (load testing, observability pipelines, test data)
  - For each: features, community size (GitHub stars, downloads), positioning, licensing
- Identify market trends:
  - SIEM/observability industry direction
  - Test data generation demand
  - Open-source adoption patterns
- If a focus area was specified, prioritize that area

Present market scan findings to TL.

### Phase 2: Internal Audit

**Delegate to researcher agent** (runs in **parallel** with Phase 1):

- Analyze Eventum's community health:
  ```bash
  gh repo view eventum-generator/eventum --json stargazerCount,forkCount,watchers
  gh issue list --repo eventum-generator/eventum --limit 100 --state open --json title,labels,createdAt
  gh api repos/eventum-generator/eventum/traffic/views
  ```
- Review GitHub Discussions for user feedback patterns
- Catalog current capabilities: plugins, integrations, content packs
- Identify gaps: what do users ask for that Eventum doesn't have?

Present internal audit findings to TL.

### Phase 3: Synthesis

**Delegate to product-strategist agent**:

- Combine market scan (Phase 1) with internal audit (Phase 2)
- Produce a Strategy Report:
  - Executive summary
  - Competitive positioning (strengths, weaknesses, opportunities)
  - Feature recommendations with impact/effort matrix
  - Growth opportunity rankings
  - Concrete action items

**Checkpoint**: Present strategy to the user for approval before proceeding to content planning.

### Phase 4: Content Plan

**Delegate to content-growth agent**:

- Based on the approved strategy, draft a content calendar:
  - Blog posts to write (topics, target audience, keywords)
  - Community engagement actions (Discussions, Reddit, Dev.to)
  - External publication opportunities (Habr, conferences)
  - Timeline and priority order
- For the highest-priority item, draft an outline or brief

Present content plan to TL.

### Phase 5: Present

**TL directly**:

Present to the user:
- Strategy summary (key findings, top 3 recommendations)
- Content plan overview
- Suggested next steps (which items to tackle first)

### Important

- Phase 1 and Phase 2 run in parallel - they are independent.
- This is a strategic review, not an implementation task. No code changes are made.
- All recommendations are advisory - the user makes final decisions.
- Track progress with the todo list throughout.
- If market data is insufficient for confident recommendations, say so rather than guessing.
