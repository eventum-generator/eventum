---
paths:
  - "../docs/lib/hub-data/**/*.ts"
---

# Hub Rules

The Hub is a catalog of content-pack generators at `/hub`. Entries are TypeScript data files under `../docs/lib/hub-data/` - the UI reads them at build time.

## Source of truth

The content-pack generator is the source of truth - its files, its README. The Hub entry is a compact summary compiled from the README: `slug`, `generatorId`, counts, frequencies, parameters, sample JSON all come from there, never invented. When the generator or its README changes, resync the Hub entry or it drifts.

## Registration

A generator file is not visible until it's imported and listed in `index.ts`. Omitting the registration silently hides the entry.

## Categories

`category` is a fixed `CategoryId` union. Use an existing value; adding a new category means updating `hub-categories.ts`.
