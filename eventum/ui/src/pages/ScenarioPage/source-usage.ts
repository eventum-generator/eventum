import { GlobalsUsage } from '@/api/routes/scenarios/schemas';

export type WarningType = 'dynamic_key' | 'update_call';

export interface SourceUsageEntry {
  /** File path relative to the generator root. */
  path: string;
  /** Unique global-state keys this file writes. */
  writes: string[];
  /** Unique global-state keys this file reads. */
  reads: string[];
  /** Analyzer caveats for this file (keys may be incomplete). */
  warnings: WarningType[];
}

/** Human-readable explanation for each analyzer warning, shown on hover. */
export const WARNING_LABEL: Record<WarningType, string> = {
  dynamic_key:
    'Uses a computed key - some keys touched here may not be listed.',
  update_call: 'Uses update() - the written keys may be incomplete.',
};

/**
 * Group a generator's globals usage by file, merging writes, reads and
 * analyzer warnings into one entry per file (deduped, sorted). A file that
 * only produced a warning still appears, so nothing the analyzer flagged is
 * hidden.
 */
export function buildSourceUsage(usage?: GlobalsUsage): SourceUsageEntry[] {
  const map = new Map<string, SourceUsageEntry>();

  const entryFor = (path: string): SourceUsageEntry => {
    let entry = map.get(path);
    if (!entry) {
      entry = { path, writes: [], reads: [], warnings: [] };
      map.set(path, entry);
    }
    return entry;
  };

  for (const write of usage?.writes ?? []) {
    const entry = entryFor(write.path);
    if (!entry.writes.includes(write.key)) entry.writes.push(write.key);
  }
  for (const read of usage?.reads ?? []) {
    const entry = entryFor(read.path);
    if (!entry.reads.includes(read.key)) entry.reads.push(read.key);
  }
  for (const warning of usage?.warnings ?? []) {
    const entry = entryFor(warning.path);
    if (!entry.warnings.includes(warning.type))
      entry.warnings.push(warning.type);
  }

  return [...map.values()].sort((a, b) => a.path.localeCompare(b.path));
}
