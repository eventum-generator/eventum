---
name: promote
description: Create promotional content for a feature, release, or topic - blog post, social media drafts, community engagement materials.
user-invokable: true
argument-hint: "<topic> (e.g. 'v2.1.0 release', 'UDP output plugin', 'SIEM testing use case')"
context: fork
---

## Current state
- Recent releases: !`gh release list --limit 3`
- Recent blog posts: !`ls ../docs/content/blog/ | tail -5`

## Promote

Orchestrate the creation of promotional content for **$ARGUMENTS** by delegating to your team of agents.

Parse the argument as the topic to promote. If not provided, ask the user.

### Phase 1: Research

**Delegate to researcher agent**:

- Understand the topic thoroughly:
  - If it's a feature/plugin: read the code, docs, changelog entry
  - If it's a release: read the changelog, compare with previous version
  - If it's a use case: read relevant docs, tutorials, examples
- Identify the key value proposition - what makes this worth talking about?
- Find comparable content from competitors (how do they promote similar features?)

Present research findings to TL.

### Phase 2: Strategy

**Delegate to product-strategist agent**:

- Based on research findings, define the promotion strategy:
  - Target audience (personas, job titles, communities)
  - Key messages (what to emphasize, what differentiates Eventum)
  - Best platforms for this specific topic
  - Tone and angle for each platform
- Consider timing (is there a relevant industry event, trend, or conversation to piggyback on?)

**Checkpoint**: Present strategy and target audience to the user before creating content.

### Phase 3: Create Content

**Delegate to content-growth agent**:

- Create the primary content piece (usually a blog post):
  - Write MDX blog post at `../docs/content/blog/` (if approved by user)
  - Or write inline in the report (if user prefers not to commit to the blog yet)
- Create platform-specific adaptations:
  - GitHub Discussion draft (if relevant)
  - Reddit post draft (community-native tone)
  - Twitter/X thread or announcement
  - LinkedIn post (if enterprise-relevant)
  - Habr article draft (if technically deep enough)
  - Dev.to article (if tutorial-focused)
- Include publishing notes for each platform

Present all drafts to TL.

### Phase 4: Review

**Delegate to code-reviewer agent**:

- Review all content for **technical accuracy only**:
  - Are feature descriptions correct?
  - Are code examples valid and runnable?
  - Are performance claims substantiated?
  - Are version numbers and links correct?
- Do NOT review writing style or marketing effectiveness - only factual accuracy

If verdict is **FAIL**: route findings to **content-growth** agent to fix, then re-review. Loop until **PASS**. If the loop does not converge after 3 cycles, stop and consult the user.

### Phase 5: Present

**TL directly**:

Present to the user:
- All content drafts (blog post, platform posts)
- Platform recommendations with reasoning
- Suggested publishing timeline
- Any content that was written to files (paths)

### Important

- All content is a **draft** - the user reviews and publishes manually on external platforms.
- Blog posts written to `../docs/content/blog/` can be committed if the user approves.
- Code reviewer checks technical accuracy, not writing quality. This is intentional.
- Track progress with the todo list throughout.
- If blocked or uncertain about the topic, ask the user rather than guessing.
