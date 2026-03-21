---
name: competitive-analysis
description: Deep-dive competitive analysis of a specific tool or product category. Produces positioning recommendations and feature gap analysis.
user-invokable: true
argument-hint: "<competitor-or-category> (e.g. 'vector', 'logstash', 'load-testing-tools')"
context: fork
---

## Current state
- Current features: !`grep -c 'class.*Plugin' eventum/plugins/**/plugin.py 2>/dev/null || echo "N/A"`
- GitHub stats: !`gh api repos/eventum-dev/eventum --jq '{stars: .stargazers_count, forks: .forks_count, issues: .open_issues_count}'`

## Competitive Analysis

Orchestrate a deep-dive competitive analysis of **$ARGUMENTS** by delegating to your team of agents.

Parse the argument as either a specific competitor tool or a product category. If not provided, ask the user.

### Phase 1: Research

**Delegate to researcher agent**:

- Deep dive on the competitor or category:
  - **If specific tool**: GitHub repo (stars, contributors, commit frequency, issues), documentation, feature set, architecture, pricing/licensing, community (Discord, Slack, forums), recent releases and roadmap
  - **If category**: Map the landscape -- list all relevant tools, categorize by approach, identify market leaders and emerging players
- Gather quantitative data:
  ```bash
  # Example for GitHub-hosted competitors
  gh api repos/<owner>/<repo> --jq '.stargazers_count, .forks_count, .open_issues_count'
  ```
- Read their documentation to understand positioning claims and target audience
- Search for user reviews, comparisons, community sentiment

Present research findings to TL.

### Phase 2: Analyze

**Delegate to product-strategist agent**:

- Produce a competitive analysis:
  - **Feature comparison matrix**: Eventum vs competitor(s) across key dimensions
  - **SWOT analysis**: Strengths, Weaknesses, Opportunities, Threats
  - **Positioning map**: Where does each tool sit in the market?
  - **User experience comparison**: Onboarding, documentation, ease of use
  - **Community comparison**: Size, activity, governance, contributor experience
- Identify specific areas where Eventum is stronger and weaker

**Checkpoint**: Present the analysis to the user before generating action items.

### Phase 3: Action Items

**Delegate to product-strategist agent**:

Based on the analysis and user feedback, produce concrete recommendations:

- **Feature proposals**: Specific features that would close competitive gaps (with priority)
- **Positioning opportunities**: How to differentiate Eventum in messaging and content
- **Content opportunities**: Comparison articles, migration guides, "Why Eventum" pages
- **Integration opportunities**: Partnerships or integrations that would strengthen positioning
- **Quick wins**: Low-effort changes that immediately improve competitive position

### Phase 4: Present

**TL directly**:

Present to the user:
- Competitive analysis summary
- Feature gap matrix (visual table)
- Top 3 recommended actions with impact/effort
- Content opportunities (potential blog posts, comparison pages)

### Important

- Be objective -- genuine competitive analysis requires honesty about both strengths and weaknesses.
- This is an analytical task, not an implementation task. No code changes are made.
- Feature proposals go into the backlog as GitHub issues (if user approves).
- Track progress with the todo list throughout.
- If the competitor is not well-known or has limited public information, report what you found and note the gaps.
