---
paths:
  - "../docs/content/blog/**/*.mdx"
---

# Blog Post Rules

Blog posts live in `../docs/content/blog/` - release announcements, launches, feature highlights. Journalistic storytelling, not reference.

## Frontmatter

```yaml
---
title: "Post Title"
description: "One-line summary shown in the blog index and OG cards."
date: "YYYY-MM-DDTHH:MM:SS"
author: "Eventum Team"
tags:
  - release  # or `announcement` for non-release posts
cover: "/blog/<slug>/cover.png"  # optional, index card thumbnail
pinned: true  # optional, places the post in the Featured slot
---
```

## Voice

- Plain present tense: "Eventum now supports X", not "We are thrilled to announce X".
- Banned hype: `revolutionary`, `game-changing`, `powerful`, `seamless`, `unleash`.
- Em dash (`—`) allowed for rhythm.

## Featured slot

The blog index shows one Featured post: `posts.find(p => p.pinned) ?? posts[0]`. Non-typical posts (product launches, major milestones) set `pinned: true` to take that slot. When pinning a new post, un-pin the previous one - first-match wins otherwise.

## Post types

### Release announcement (`eventum-X-Y-Z.mdx`)

Title lists the headline features (`"Eventum X.Y.Z: <A>, <B>, <C>"`). Open with a short paragraph naming the headline feature, then one H2 per major feature - prose plus whatever fits (screenshot, config snippet). Inline doc links where readers would want more depth. Close with a link to the changelog.

### Launch / announcement (e.g. `eventum-hub.mdx`)

Journalistic launch for non-release events - product launches, major milestones. Set `pinned: true` and `cover: "..."` to take the Featured slot. Free-form structure; typical ingredients in roughly this order: what's launching and a link to it, a hero image, the problem it solves, what it is, how to use it, a closing call-to-action.

### Feature highlight

One feature, one spotlight. Longer and more detailed than a release-announcement section - typically walks through why it exists, what it does, how to use it, and links to the related docs.

## Images

- Plain markdown `![Alt text](/blog/<slug>/image.png)` works for any image and is the default choice.
- When both light and dark variants exist (usually UI screenshots), `<ThemedImage lightSrc="..." darkSrc="..." alt="..." className="rounded-lg border mt-2" />` picks the right one per theme.

## Length

No fixed target - length adapts to what's shipping. Content that outgrows the blog voice - long reference material, deep walkthroughs - is better as a standalone docs article; link to it from the post.

## Honesty

- Every feature claim must be verifiable against the code or docs.
- Don't hide limitations - mention known caveats briefly.
- Don't pre-announce unshipped features. Posts ship with the release, not before.

## SEO

- `description` doubles as the OG card text - must read stand-alone, not repeat the title.
- OG images are auto-generated from `../docs/app/og/blog/` - verify rendering before publishing.
