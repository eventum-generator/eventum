import { GlobalsUsage } from '@/api/routes/scenarios/schemas';

export type WarningType = 'dynamic_key' | 'update_call';

export interface TemplateUsageEntry {
  /** Template path relative to the generator root. */
  template: string;
  /** Unique global-state keys this template writes. */
  writes: string[];
  /** Unique global-state keys this template reads. */
  reads: string[];
  /** Analyzer caveats for this template (keys may be incomplete). */
  warnings: WarningType[];
}

/** Human-readable explanation for each analyzer warning, shown on hover. */
export const WARNING_LABEL: Record<WarningType, string> = {
  dynamic_key:
    'Uses a computed key - some keys touched here may not be listed.',
  update_call: 'Uses update() - the written keys may be incomplete.',
};

/**
 * Group a generator's globals usage by template, merging writes, reads and
 * analyzer warnings into one entry per template (deduped, sorted). A template
 * that only produced a warning still appears, so nothing the analyzer flagged
 * is hidden.
 */
export function buildTemplateUsage(usage?: GlobalsUsage): TemplateUsageEntry[] {
  const map = new Map<string, TemplateUsageEntry>();

  const entryFor = (template: string): TemplateUsageEntry => {
    let entry = map.get(template);
    if (!entry) {
      entry = { template, writes: [], reads: [], warnings: [] };
      map.set(template, entry);
    }
    return entry;
  };

  for (const write of usage?.writes ?? []) {
    const entry = entryFor(write.template);
    if (!entry.writes.includes(write.key)) entry.writes.push(write.key);
  }
  for (const read of usage?.reads ?? []) {
    const entry = entryFor(read.template);
    if (!entry.reads.includes(read.key)) entry.reads.push(read.key);
  }
  for (const warning of usage?.warnings ?? []) {
    const entry = entryFor(warning.template);
    if (!entry.warnings.includes(warning.type))
      entry.warnings.push(warning.type);
  }

  return [...map.values()].sort((a, b) => a.template.localeCompare(b.template));
}
